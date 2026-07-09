"""Remote mode: live existence checks against a source API.

Remote mode mirrors cache mode, with membership in a pinned snapshot replaced by
live existence via a resolver. A resolver names one API and knows how to build a
lookup URL, read a status and body into an existence verdict, and reduce a
response to the minimal body worth caching. Three resolvers ship here: OLS (EBI
Ontology Lookup Service) for the ontology sources, Ensembl for stable ids, and
UniProt for protein accessions.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ._cache import cache_dir
from ._pattern import _species_ok, _suggest, matches
from ._registry import Source

_USER_AGENT = "biogate/0.1 (+https://github.com/samuelbharti/biogate)"
_OLS_BASE = "https://www.ebi.ac.uk/ols4/api"


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
    id prefix, the response body, or neither depending on the source.
    """

    name: str
    subkey: Callable[[Source], str]
    url: Callable[[Source, str], str]
    exists: Callable[[int, dict | None], bool]
    cache_body: Callable[[int, dict | None], dict | None]
    species_ok: Callable[[Source, str, dict | None, object], bool]


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
        return {"page": {"totalElements": _ols_count(body)}}
    return None


def _ols_species_ok(source: Source, ident: str, body: dict | None, species) -> bool:
    # OLS terms are not species scoped; existence is the whole verdict.
    return True


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


_OLS = Resolver(
    name="ols",
    subkey=_ols_subkey,
    url=_ols_url,
    exists=_ols_exists,
    cache_body=_ols_cache_body,
    species_ok=_ols_species_ok,
)
_ENSEMBL = Resolver(
    name="ensembl",
    subkey=_ensembl_subkey,
    url=_ensembl_url,
    exists=_ensembl_exists,
    cache_body=_ensembl_cache_body,
    species_ok=_ensembl_species_ok,
)
_UNIPROT = Resolver(
    name="uniprot",
    subkey=_uniprot_subkey,
    url=_uniprot_url,
    exists=_uniprot_exists,
    cache_body=_uniprot_cache_body,
    species_ok=_uniprot_species_ok_id,
)

_RESOLVERS = {"ols": _OLS, "ensembl": _ENSEMBL, "uniprot": _UNIPROT}


def _remote_cache_path(resolver_name: str, subkey: str, ident: str) -> Path:
    """On-disk path for a cached remote response."""
    return (
        cache_dir()
        / "remote"
        / resolver_name
        / subkey
        / f"{ident.replace(':', '_')}.json"
    )


def _remote_lookup(
    resolver: Resolver,
    source: Source,
    ident: str,
    species=None,
    refresh: bool = False,
) -> bool:
    """Whether ``ident`` exists and matches ``species``, cache backed.

    The cache is keyed by id only; species is compared at read time against the
    cached body, so one cached response answers any species. An indeterminate
    status raises before the cache is written, so a response that gives no
    definite answer is never persisted.
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
                return False
            return resolver.species_ok(source, ident, body, species)
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
        return False
    return resolver.species_ok(source, ident, body, species)


def _get_resolver(source: Source) -> Resolver:
    """Return the resolver for a source or raise ``NoResolverError``."""
    remote = source.remote
    if not remote or remote.get("resolver") not in _RESOLVERS:
        raise NoResolverError(f"No remote resolver for {source.key!r}.")
    return _RESOLVERS[remote["resolver"]]


def _resolve_ids(
    resolver: Resolver, source: Source, ids: list[str], species
) -> dict[str, bool]:
    """Resolve existence and species for a batch of ids through one resolver."""
    return {ident: _remote_lookup(resolver, source, ident, species) for ident in ids}


def remote_verdicts(
    source: Source, items: list[str], species=None
) -> list[tuple[bool, str | None, str | None]]:
    """Return ``(valid, normalized, suggestion)`` per item via live existence.

    Well-formed inputs are looked up directly. Malformed inputs offer a
    suggestion only when a correction candidate exists remotely. When
    ``species`` is given, an id that exists but belongs to a different species
    is not valid. Existence is resolved for the whole batch in a single
    resolver call.
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
    exists = _resolve_ids(resolver, source, sorted(need), species) if need else {}
    verdicts: list[tuple[bool, str | None, str | None]] = []
    for well_formed, value in plans:
        if well_formed:
            if exists.get(value):
                verdicts.append((True, value, None))
            else:
                verdicts.append((False, None, None))
        elif value is not None and exists.get(value):
            verdicts.append((False, None, value))
        else:
            verdicts.append((False, None, None))
    return verdicts
