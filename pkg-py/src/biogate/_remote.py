"""Remote mode: live existence checks against a source API.

Remote mode mirrors cache mode, with membership in a pinned snapshot replaced by
live existence via a resolver. A resolver names one API and knows how to build a
lookup URL, read a status and body into an existence verdict, and reduce a
response to the minimal body worth caching. Six resolvers ship here: OLS (EBI
Ontology Lookup Service) for the ontology sources, Ensembl for stable ids,
UniProt for protein accessions, Mutalyzer for HGVS variant descriptions, dbSNP
for reference SNP ids, and RCSB PDB for structure ids.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ._cache import cache_dir
from ._pattern import _species_ok, _suggest, matches
from ._registry import Source

_USER_AGENT = "biogate/0.1 (+https://github.com/samuelbharti/biogate)"
_OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
_MUTALYZER_BASE = "https://mutalyzer.nl/api/normalize/"
_RCSB_BASE = "https://data.rcsb.org/rest/v1/core/entry/"
_UNSAFE_IDENT = re.compile(r"[^A-Za-z0-9._-]")


def _safe_ident(ident: str) -> str:
    """Turn an identifier into a safe file name.

    Every character outside ``[A-Za-z0-9._-]`` becomes ``_``. This keeps an id
    with a colon, a slash, or a ``>`` (such as an HGVS variant) usable as a cache
    or fixture file name across platforms. The rule matches ``mode-remote.R``.
    """
    return _UNSAFE_IDENT.sub("_", ident)


class RemoteError(RuntimeError):
    """Raised when a remote check fails to get a definite answer."""


class NoResolverError(ValueError):
    """Raised when a source has no remote resolver."""


def _parse_body(text: str) -> dict | None:
    """Parse a JSON body, tolerating an empty or non-JSON payload.

    A proxy or outage can return HTML instead of JSON. That is not a parse
    error to raise here; the status is what decides the verdict, so a body that
    does not parse becomes ``None`` and the caller classifies by status.
    """
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _http_get(url: str, timeout: int = 30) -> tuple[int, dict | None]:
    """Fetch ``url`` and return ``(status, parsed_json_or_None)``.

    This is the network seam. HTTP error statuses such as 404 flow through as a
    status. Network and timeout failures raise ``RemoteError``.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = response.status
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, _parse_body(error.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RemoteError(f"Remote request failed for {url!r}: {error}") from error
    return status, _parse_body(text)


def _ols_count(body: dict | None) -> int:
    """The matching-term count in an OLS response, 0 when absent or malformed."""
    page = (body or {}).get("page") or {}
    total = page.get("totalElements") or 0
    try:
        return int(total)
    except (TypeError, ValueError):
        return 0


def _uniprot_active(body: dict | None) -> bool:
    """Whether a UniProt entry is an active (non-deleted) UniProtKB record."""
    return str((body or {}).get("entryType", "")).startswith("UniProtKB")


def _normalize_obo(s: str | None) -> str | None:
    """Normalize a successor reference to a colon obo_id.

    Accepts a short form such as ``"GO_0006915"`` or a full IRI such as
    ``"http://purl.obolibrary.org/obo/MONDO_0005016"``. Takes the substring after
    the last slash, then turns the first underscore into a colon. A missing or
    empty value returns None.
    """
    if not s:
        return None
    tail = s.rsplit("/", 1)[-1]
    return tail.replace("_", ":", 1)


def _species_taxon(species_block: dict, species) -> int | None:
    """Resolve ``species`` to a taxon id using the source species map.

    A name in the map resolves to its taxon. A species given directly as a
    number (an int or float that is not a bool, or an all-digit string) is
    taken as the taxon id itself. Anything else is unknown and returns None.
    """
    for entry in species_block.get("map", []):
        if str(entry.get("name")) == str(species):
            return entry.get("taxon")
    numeric = isinstance(species, (int, float)) and not isinstance(species, bool)
    if numeric or str(species).isdigit():
        return int(species)
    return None


def _uniprot_species_ok(source: Source, body: dict | None, species) -> bool:
    """Whether a UniProt entry's organism matches the requested ``species``.

    Lenient: a missing species, a source without the organism scheme, a species
    outside the map, or a body with no organism taxon id all pass. Otherwise the
    entry's organism taxon id must equal the requested taxon.
    """
    if species is None:
        return True
    block = source.species
    if not block or block.get("scheme") != "uniprot_organism":
        return True
    expected = _species_taxon(block, species)
    if expected is None:
        return True
    body_taxon = ((body or {}).get("organism") or {}).get("taxonId")
    if body_taxon is None:
        return True
    return int(body_taxon) == int(expected)


@dataclass(frozen=True)
class Resolver:
    """One remote API: how to address it and how to read its answers.

    ``subkey`` names the cache and fixture subdirectory for a source (the
    ontology for OLS, a fixed endpoint name otherwise). ``url`` builds the
    lookup URL. ``exists`` turns ``(status, body)`` into a verdict and raises
    ``RemoteError`` for an indeterminate status. ``cache_body`` reduces a
    response to the minimal body worth persisting. ``species_ok`` decides, for
    an id that exists, whether it belongs to the requested species; it reads the
    id prefix, the response body, or neither depending on the source. ``retired``
    decides, for an id that exists, whether it is obsolete and returns
    ``(is_retired, successor)`` with the successor as a colon obo_id or None.
    """

    name: str
    subkey: Callable[[Source], str]
    url: Callable[[Source, str], str]
    exists: Callable[[int, dict | None], bool]
    cache_body: Callable[[int, dict | None], dict | None]
    species_ok: Callable[[Source, str, dict | None, object], bool]
    retired: Callable[[Source, dict | None], tuple[bool, str | None]]


def _ols_subkey(source: Source) -> str:
    return source.remote["ols_ontology"]


def _ols_url(source: Source, ident: str) -> str:
    return (
        f"{_OLS_BASE}/ontologies/{source.remote['ols_ontology']}/terms?obo_id={ident}"
    )


def _ols_exists(status: int, body: dict | None) -> bool:
    if status == 200:
        return _ols_count(body) >= 1
    if status == 404:
        return False
    raise RemoteError(f"OLS returned unexpected status {status}.")


def _ols_cache_body(status: int, body: dict | None) -> dict | None:
    if status == 200:
        terms = ((body or {}).get("_embedded") or {}).get("terms")
        term = (terms[0] if terms else None) or {}
        return {
            "page": {"totalElements": _ols_count(body)},
            "_embedded": {
                "terms": [
                    {
                        "is_obsolete": bool(term.get("is_obsolete")),
                        "term_replaced_by": term.get("term_replaced_by"),
                    }
                ]
            },
        }
    return None


def _ols_species_ok(source: Source, ident: str, body: dict | None, species) -> bool:
    # OLS terms are not species scoped; existence is the whole verdict.
    return True


def _ols_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    terms = ((body or {}).get("_embedded") or {}).get("terms")
    if not terms:
        return False, None
    term = terms[0] or {}
    if term.get("is_obsolete"):
        return True, _normalize_obo(term.get("term_replaced_by"))
    return False, None


def _ensembl_subkey(source: Source) -> str:
    return "id"


def _ensembl_url(source: Source, ident: str) -> str:
    return f"https://rest.ensembl.org/lookup/id/{ident}?content-type=application/json"


def _ensembl_exists(status: int, body: dict | None) -> bool:
    # Ensembl answers 400 for a well-formed but unknown id; a 404 is treated as
    # absent too.
    if status == 200:
        return True
    if status in (400, 404):
        return False
    raise RemoteError(f"Ensembl returned unexpected status {status}.")


def _ensembl_cache_body(status: int, body: dict | None) -> dict | None:
    return None


def _ensembl_species_ok(source: Source, ident: str, body: dict | None, species) -> bool:
    # Ensembl encodes species in the id prefix, so the offline check suffices.
    return _species_ok(source, ident, species)


def _ensembl_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    # Ensembl existence has no obsolete-with-successor concept here.
    return False, None


def _uniprot_subkey(source: Source) -> str:
    return "uniprotkb"


def _uniprot_url(source: Source, ident: str) -> str:
    return f"https://rest.uniprot.org/uniprotkb/{ident}.json"


def _uniprot_exists(status: int, body: dict | None) -> bool:
    if status == 200:
        return _uniprot_active(body)
    if status == 404:
        return False
    raise RemoteError(f"UniProt returned unexpected status {status}.")


def _uniprot_cache_body(status: int, body: dict | None) -> dict | None:
    if status == 200:
        taxon = ((body or {}).get("organism") or {}).get("taxonId")
        return {
            "entryType": (body or {}).get("entryType"),
            "organism": {"taxonId": taxon},
        }
    return None


def _uniprot_species_ok_id(
    source: Source, ident: str, body: dict | None, species
) -> bool:
    # A UniProt accession does not encode species, so read it from the body.
    return _uniprot_species_ok(source, body, species)


def _uniprot_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    # UniProt retirement is modeled as inactive existence, not a successor here.
    return False, None


def _mutalyzer_subkey(source: Source) -> str:
    return "normalize"


def _mutalyzer_url(source: Source, ident: str) -> str:
    return _MUTALYZER_BASE + urllib.parse.quote(ident, safe="")


def _mutalyzer_exists(status: int, body: dict | None) -> bool:
    # Mutalyzer normalizes a valid variant (200) and rejects one that is not
    # consistent with its reference (422): wrong reference base, a coordinate out
    # of range, or a reference that does not exist.
    if status == 200:
        return True
    if status == 422:
        return False
    raise RemoteError(f"Mutalyzer returned unexpected status {status}.")


def _mutalyzer_cache_body(status: int, body: dict | None) -> dict | None:
    # The status carries the whole verdict, so no body is worth persisting.
    return None


def _mutalyzer_species_ok(
    source: Source, ident: str, body: dict | None, species
) -> bool:
    # An HGVS variant is named against a specific reference, not a species map.
    return True


def _mutalyzer_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    return False, None


def _dbsnp_subkey(source: Source) -> str:
    return "refsnp"


def _dbsnp_url(source: Source, ident: str) -> str:
    number = ident[2:] if ident[:2].lower() == "rs" else ident
    return f"https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/{number}"


def _dbsnp_merged_into(body: dict | None) -> str | None:
    """The primary rsID number a merged record points to, or None for a primary."""
    merged = (body or {}).get("merged_snapshot_data") or {}
    ids = merged.get("merged_into") or []
    return str(ids[0]) if ids else None


def _dbsnp_exists(status: int, body: dict | None) -> bool:
    if status == 200:
        return True
    if status == 404:
        return False
    raise RemoteError(f"dbSNP returned unexpected status {status}.")


def _dbsnp_cache_body(status: int, body: dict | None) -> dict | None:
    # Persist only the merge pointer; a primary record needs no body.
    if status == 200:
        target = _dbsnp_merged_into(body)
        if target:
            return {"merged_snapshot_data": {"merged_into": [target]}}
    return None


def _dbsnp_species_ok(source: Source, ident: str, body: dict | None, species) -> bool:
    return True


def _dbsnp_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    # A merged rsID still resolves but is not current; suggest the primary id.
    target = _dbsnp_merged_into(body)
    if target:
        return True, f"rs{target}"
    return False, None


def _pdb_subkey(source: Source) -> str:
    return "entry"


def _pdb_url(source: Source, ident: str) -> str:
    return _RCSB_BASE + ident


def _pdb_exists(status: int, body: dict | None) -> bool:
    if status == 200:
        return True
    if status == 404:
        return False
    raise RemoteError(f"RCSB PDB returned unexpected status {status}.")


def _pdb_cache_body(status: int, body: dict | None) -> dict | None:
    # The status carries the whole verdict, so no body is worth persisting.
    return None


def _pdb_species_ok(source: Source, ident: str, body: dict | None, species) -> bool:
    # A structure is not species scoped for this existence check.
    return True


def _pdb_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    # Existence only; an obsoleted-with-successor entry is not modeled yet.
    return False, None


_OLS = Resolver(
    name="ols",
    subkey=_ols_subkey,
    url=_ols_url,
    exists=_ols_exists,
    cache_body=_ols_cache_body,
    species_ok=_ols_species_ok,
    retired=_ols_retired,
)
_ENSEMBL = Resolver(
    name="ensembl",
    subkey=_ensembl_subkey,
    url=_ensembl_url,
    exists=_ensembl_exists,
    cache_body=_ensembl_cache_body,
    species_ok=_ensembl_species_ok,
    retired=_ensembl_retired,
)
_UNIPROT = Resolver(
    name="uniprot",
    subkey=_uniprot_subkey,
    url=_uniprot_url,
    exists=_uniprot_exists,
    cache_body=_uniprot_cache_body,
    species_ok=_uniprot_species_ok_id,
    retired=_uniprot_retired,
)

_MUTALYZER = Resolver(
    name="mutalyzer",
    subkey=_mutalyzer_subkey,
    url=_mutalyzer_url,
    exists=_mutalyzer_exists,
    cache_body=_mutalyzer_cache_body,
    species_ok=_mutalyzer_species_ok,
    retired=_mutalyzer_retired,
)

_DBSNP = Resolver(
    name="dbsnp",
    subkey=_dbsnp_subkey,
    url=_dbsnp_url,
    exists=_dbsnp_exists,
    cache_body=_dbsnp_cache_body,
    species_ok=_dbsnp_species_ok,
    retired=_dbsnp_retired,
)

_PDB = Resolver(
    name="pdb",
    subkey=_pdb_subkey,
    url=_pdb_url,
    exists=_pdb_exists,
    cache_body=_pdb_cache_body,
    species_ok=_pdb_species_ok,
    retired=_pdb_retired,
)

_RESOLVERS = {
    "ols": _OLS,
    "ensembl": _ENSEMBL,
    "uniprot": _UNIPROT,
    "mutalyzer": _MUTALYZER,
    "dbsnp": _DBSNP,
    "pdb": _PDB,
}


def _remote_cache_path(resolver_name: str, subkey: str, ident: str) -> Path:
    """On-disk path for a cached remote response."""
    return (
        cache_dir() / "remote" / resolver_name / subkey / f"{_safe_ident(ident)}.json"
    )


def _post_existence(
    resolver: Resolver, source: Source, ident: str, body: dict | None, species
) -> tuple[bool, str | None]:
    """Verdict for an id already confirmed to exist: species then retirement."""
    if not resolver.species_ok(source, ident, body, species):
        return False, None
    is_retired, successor = resolver.retired(source, body)
    if is_retired:
        return False, successor
    return True, None


def _remote_lookup(
    resolver: Resolver,
    source: Source,
    ident: str,
    species=None,
    refresh: bool = False,
) -> tuple[bool, str | None]:
    """Return ``(valid, suggestion)`` for ``ident``, cache backed.

    An id that exists, matches ``species``, and is not obsolete is valid with no
    suggestion. An id that exists but is obsolete is not valid and carries its
    successor as the suggestion. An id that is absent or belongs to another
    species is not valid with no suggestion. The cache is keyed by id only;
    species is compared at read time against the cached body, so one cached
    response answers any species. An indeterminate status raises before the
    cache is written, so a response that gives no definite answer is never
    persisted.
    """
    path = _remote_cache_path(resolver.name, resolver.subkey(source), ident)
    if not refresh and path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            status, body = cached["status"], cached.get("body")
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # A corrupt or partial cache file is ignored and refetched.
        else:
            if not resolver.exists(status, body):
                return False, None
            return _post_existence(resolver, source, ident, body, species)
    url = resolver.url(source, ident)
    status, body = _http_get(url)
    result = resolver.exists(status, body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"status": status, "body": resolver.cache_body(status, body), "url": url}
        ),
        encoding="utf-8",
    )
    if not result:
        return False, None
    return _post_existence(resolver, source, ident, body, species)


def _get_resolver(source: Source) -> Resolver:
    """Return the resolver for a source or raise ``NoResolverError``."""
    remote = source.remote
    if not remote or remote.get("resolver") not in _RESOLVERS:
        raise NoResolverError(f"No remote resolver for {source.key!r}.")
    return _RESOLVERS[remote["resolver"]]


def _resolve_ids(
    resolver: Resolver, source: Source, ids: list[str], species
) -> dict[str, tuple[bool, str | None]]:
    """Resolve validity and any successor for a batch of ids through one resolver."""
    return {ident: _remote_lookup(resolver, source, ident, species) for ident in ids}


def remote_verdicts(
    source: Source, items: list[str], species=None
) -> list[tuple[bool, str | None, str | None]]:
    """Return ``(valid, normalized, suggestion)`` per item via live existence.

    Well-formed inputs are looked up directly; one that exists but is obsolete is
    not valid and carries its successor as the suggestion. Malformed inputs offer
    a suggestion only when a correction candidate exists remotely. When
    ``species`` is given, an id that exists but belongs to a different species is
    not valid. Existence is resolved for the whole batch in a single resolver
    call.
    """
    resolver = _get_resolver(source)
    plans: list[tuple[bool, str | None]] = []
    need: set[str] = set()
    for item in items:
        if matches(source.pattern, item):
            plans.append((True, item))
            need.add(item)
        else:
            candidate = _suggest(source, item)
            plans.append((False, candidate))
            if candidate is not None:
                need.add(candidate)
    resolved = _resolve_ids(resolver, source, sorted(need), species) if need else {}
    verdicts: list[tuple[bool, str | None, str | None]] = []
    for well_formed, value in plans:
        valid, successor = resolved.get(value, (False, None))
        if well_formed:
            if valid:
                verdicts.append((True, value, None))
            else:
                verdicts.append((False, None, successor))
        elif value is not None and valid:
            verdicts.append((False, None, value))
        else:
            verdicts.append((False, None, None))
    return verdicts
