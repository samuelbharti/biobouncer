"""Remote mode: live existence checks against a source API.

Remote mode mirrors cache mode, with membership in a pinned snapshot replaced by
live existence via a resolver. A resolver names one API and knows how to build a
lookup URL, read a status and body into an existence verdict, and reduce a
response to the minimal body worth caching. The resolvers cover OLS (EBI
Ontology Lookup Service) for the ontology sources, Ensembl for stable ids,
UniProt for protein accessions, Mutalyzer for HGVS variant descriptions, dbSNP
for reference SNP ids, RCSB PDB for structure ids, ChEMBL for compound and other
entity ids, Reactome for pathway stable ids, the EBI InterPro API for InterPro
and Pfam accessions, Rfam for RNA families, UniParc for unique sequences, the EBI
Complex Portal for macromolecular complexes, WikiPathways for pathways, and NCBI
E-utilities for RefSeq and ClinVar accessions.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ._cache import _atomic_write_text, cache_dir
from ._pattern import _species_ok, _suggest, matches
from ._registry import Source

_USER_AGENT = "biogate/0.1 (+https://github.com/samuelbharti/biogate)"
_OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
_MUTALYZER_BASE = "https://mutalyzer.nl/api/normalize/"
_RCSB_BASE = "https://data.rcsb.org/rest/v1/core/entry/"
_CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data/chembl_id_lookup/"
_REACTOME_BASE = "https://reactome.org/ContentService/data/query/"
_INTERPRO_BASE = "https://www.ebi.ac.uk/interpro/api/entry/"
_RFAM_BASE = "https://rfam.org/family/"
_UNIPARC_BASE = "https://rest.uniprot.org/uniparc/"
_COMPLEXPORTAL_BASE = "https://www.ebi.ac.uk/intact/complex-ws/complex/"
_WIKIPATHWAYS_BASE = "https://www.wikipathways.org/wikipathways-assets/pathways/"
_PROSITE_BASE = "https://prosite.expasy.org/"
_ESUMMARY_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_ESEARCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EBISEARCH_RNACENTRAL_BASE = "https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral"
_GENENAMES_BASE = "https://rest.genenames.org/fetch/"
# RefSeq accessions split across two NCBI databases by their molecule prefix.
_REFSEQ_PROTEIN_PREFIXES = frozenset({"AP", "NP", "WP", "XP", "YP", "ZP"})
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


_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BACKOFF_BASE = 0.5  # seconds, doubling each retry: 0.5, 1.0, ...

# Politeness: the minimum seconds between requests to a host. NCBI throttles
# E-utilities to three requests a second anonymously and ten with an API key;
# other hosts are not gated here. The limiter matters only when several ids are
# checked concurrently; a single sequential caller is naturally under the limit.
_rate_meta_lock = threading.Lock()
_rate_host_locks: dict[str, threading.Lock] = {}
_rate_last_call: dict[str, float] = {}


def _min_interval_for(host: str) -> float:
    if host.endswith("ncbi.nlm.nih.gov"):
        return 0.1 if os.environ.get("NCBI_API_KEY") else 1.0 / 3.0
    return 0.0


def _host_lock(host: str) -> threading.Lock:
    with _rate_meta_lock:
        lock = _rate_host_locks.get(host)
        if lock is None:
            lock = threading.Lock()
            _rate_host_locks[host] = lock
        return lock


def _rate_limit(url: str) -> None:
    """Space out requests to a rate-limited host, per host, across threads."""
    host = urllib.parse.urlsplit(url).hostname or ""
    interval = _min_interval_for(host)
    if interval <= 0:
        return
    with _host_lock(host):
        wait = interval - (time.monotonic() - _rate_last_call.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _rate_last_call[host] = time.monotonic()


def _http_get_once(url: str, timeout: int = 30) -> tuple[int, dict | None]:
    """One request: return ``(status, parsed_json_or_None)``.

    HTTP error statuses such as 404 flow through as a status. A network or
    timeout failure raises ``RemoteError``.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = response.status
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, _parse_body(error.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RemoteError(f"Remote request failed for {url!r}: {error}") from error
    return status, _parse_body(text)


def _http_get(url: str, timeout: int = 30) -> tuple[int, dict | None]:
    """Fetch ``url`` with a bounded retry on transient failures.

    This is the network seam. A network error, a 429, or a 5xx is usually
    transient, so it is retried a few times with exponential backoff. A
    non-transient status (200, 404, and so on) returns at once for the resolver
    to classify. A network error that persists past the last attempt raises
    ``RemoteError``; a transient status that persists is returned so the resolver
    raises its own clear error.
    """
    _rate_limit(url)
    last_error: RemoteError | None = None
    status: int | None = None
    body: dict | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            status, body = _http_get_once(url, timeout)
        except RemoteError as error:
            last_error = error
        else:
            if status not in _TRANSIENT_STATUSES:
                return status, body
            last_error = None
        if attempt + 1 < _MAX_ATTEMPTS:
            time.sleep(_BACKOFF_BASE * (2**attempt))
    if last_error is not None:
        raise last_error
    return status, body


_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp() -> str:
    """The current UTC time as a second-precision ISO-8601 stamp."""
    return _utc_now().strftime(_STAMP_FORMAT)


def _remote_ttl() -> float | None:
    """Cache time-to-live in seconds from ``BIOGATE_REMOTE_TTL``, or None.

    Unset, non-numeric, or non-positive means no expiry: a cached response is
    served regardless of age. A positive value makes a cached response older
    than that many seconds stale, so it is refetched.
    """
    raw = os.environ.get("BIOGATE_REMOTE_TTL")
    if not raw:
        return None
    try:
        ttl = float(raw)
    except ValueError:
        return None
    return ttl if ttl > 0 else None


def _is_stale(fetched_at: str | None, ttl: float | None) -> bool:
    """Whether a response fetched at ``fetched_at`` has aged past ``ttl`` seconds."""
    if ttl is None:
        return False
    if not fetched_at:
        return True  # No timestamp to trust, so treat it as stale.
    try:
        stamped = datetime.strptime(fetched_at, _STAMP_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return True
    return (_utc_now() - stamped).total_seconds() > ttl


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


def _ols_obo_id(source: Source, ident: str) -> str:
    """The obo_id to query OLS with.

    Most ontology sources use the id as-is. A source may set ``obo_prefix`` to
    rewrite the id's prefix for OLS, for example ``ORPHA:558`` becomes
    ``Orphanet:558`` for the ordo ontology.
    """
    prefix = source.remote.get("obo_prefix")
    if prefix:
        return f"{prefix}:{ident.split(':', 1)[-1]}"
    return ident


def _ols_url(source: Source, ident: str) -> str:
    obo = _ols_obo_id(source, ident)
    return f"{_OLS_BASE}/ontologies/{source.remote['ols_ontology']}/terms?obo_id={obo}"


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


def _pdb_url(source: Source, ident: str) -> str:
    return _RCSB_BASE + ident


def _chembl_url(source: Source, ident: str) -> str:
    # The id-lookup endpoint resolves a ChEMBL id of any entity type (compound,
    # target, assay, document, and so on), so one call covers the whole source.
    return f"{_CHEMBL_BASE}{ident}.json"


def _reactome_url(source: Source, ident: str) -> str:
    return _REACTOME_BASE + ident


def _interpro_subkey(source: Source) -> str:
    return source.remote["interpro_db"]


def _interpro_url(source: Source, ident: str) -> str:
    # One InterPro API serves several member databases; the source names which
    # (interpro or pfam), and the entry path selects it.
    return f"{_INTERPRO_BASE}{source.remote['interpro_db']}/{ident}"


def _interpro_exists(status: int, body: dict | None) -> bool:
    # The entry endpoint answers 204 (no content) for a well-formed accession
    # that is not a current entry, and 200 when it exists.
    if status == 200:
        return True
    if status in (204, 404):
        return False
    raise RemoteError(f"InterPro returned unexpected status {status}.")


def _interpro_cache_body(status: int, body: dict | None) -> dict | None:
    # The status carries the whole verdict, so no body is worth persisting.
    return None


def _interpro_species_ok(
    source: Source, ident: str, body: dict | None, species
) -> bool:
    # A family or domain accession is not species scoped.
    return True


def _interpro_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    # Existence only; a deleted accession is reported as absent, not with a
    # successor.
    return False, None


# Shared building blocks for existence-only resolvers whose whole verdict is the
# HTTP status: 200 exists, 404 is absent, the body is never consulted, and the id
# is neither species scoped nor tracked for retirement.
def _exists_by_404(status: int, body: dict | None) -> bool:
    if status == 200:
        return True
    if status == 404:
        return False
    raise RemoteError(f"Remote source returned unexpected status {status}.")


def _no_cache_body(status: int, body: dict | None) -> dict | None:
    return None


def _species_agnostic(source: Source, ident: str, body: dict | None, species) -> bool:
    return True


def _never_retired(source: Source, body: dict | None) -> tuple[bool, str | None]:
    return False, None


def _rfam_url(source: Source, ident: str) -> str:
    return f"{_RFAM_BASE}{ident}?content-type=application/json"


def _uniparc_url(source: Source, ident: str) -> str:
    return f"{_UNIPARC_BASE}{ident}.json"


def _complexportal_url(source: Source, ident: str) -> str:
    return f"{_COMPLEXPORTAL_BASE}{ident}"


def _wikipathways_url(source: Source, ident: str) -> str:
    # The asset path repeats the id: .../pathways/WP554/WP554.gpml.
    return f"{_WIKIPATHWAYS_BASE}{ident}/{ident}.gpml"


def _prosite_url(source: Source, ident: str) -> str:
    # One ExPASy entry endpoint resolves both PROSITE patterns and profiles.
    return f"{_PROSITE_BASE}{ident}"


def _ncbi_suffix() -> str:
    """Extra E-utilities query params when an NCBI key is configured, else empty.

    NCBI throttles anonymous E-utilities at three requests a second and lifts it
    to ten with a key. When ``NCBI_API_KEY`` is set the key is added, along with
    the ``tool`` and (if ``NCBI_EMAIL`` is set) ``email`` that NCBI asks callers
    to identify themselves with. With no key the URL is unchanged, so the offline
    fixtures stay valid.
    """
    key = os.environ.get("NCBI_API_KEY")
    if not key:
        return ""
    parts = [f"api_key={urllib.parse.quote(key, safe='')}", "tool=biogate"]
    email = os.environ.get("NCBI_EMAIL")
    if email:
        parts.append(f"email={urllib.parse.quote(email, safe='')}")
    return "&" + "&".join(parts)


def _refseq_db(ident: str) -> str:
    """Pick the NCBI database for a RefSeq accession from its molecule prefix.

    Protein accessions (NP, XP, YP, WP, AP, ZP) live in the protein database; all
    other RefSeq prefixes are nucleotide records in nuccore.
    """
    prefix = ident.split("_", 1)[0].upper()
    return "protein" if prefix in _REFSEQ_PROTEIN_PREFIXES else "nuccore"


def _refseq_url(source: Source, ident: str) -> str:
    return f"{_ESUMMARY_BASE}?db={_refseq_db(ident)}&id={ident}&retmode=json{_ncbi_suffix()}"


def _esummary_has_uid(body: dict | None) -> bool:
    """Whether an E-utilities esummary response resolved the accession to a uid."""
    uids = ((body or {}).get("result") or {}).get("uids") or []
    return len(uids) >= 1


def _refseq_exists(status: int, body: dict | None) -> bool:
    # esummary answers 200 with an empty uid list and an error field for an
    # unknown accession, so existence is decided from the body, not the status.
    if status != 200:
        raise RemoteError(f"NCBI E-utilities returned unexpected status {status}.")
    return _esummary_has_uid(body)


def _refseq_cache_body(status: int, body: dict | None) -> dict | None:
    # Persist only the resolved uid list, which is all existence needs.
    if status == 200:
        uids = ((body or {}).get("result") or {}).get("uids") or []
        return {"result": {"uids": list(uids)}}
    return None


def _clinvar_url(source: Source, ident: str) -> str:
    # esearch matches a full accession of any type (VCV, RCV, or SCV), so one
    # search covers the whole source.
    return f"{_ESEARCH_BASE}?db=clinvar&term={ident}&retmode=json{_ncbi_suffix()}"


def _esearch_count(body: dict | None) -> int:
    """The hit count from an E-utilities esearch response (it is a string)."""
    result = (body or {}).get("esearchresult") or {}
    try:
        return int(result.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _clinvar_exists(status: int, body: dict | None) -> bool:
    if status != 200:
        raise RemoteError(f"NCBI E-utilities returned unexpected status {status}.")
    return _esearch_count(body) >= 1


def _clinvar_cache_body(status: int, body: dict | None) -> dict | None:
    # Persist only the hit count, which is all existence needs.
    if status == 200:
        return {"esearchresult": {"count": str(_esearch_count(body))}}
    return None


def _ebisearch_hitcount(body: dict | None) -> int:
    """The hit count from an EBI Search response, 0 when absent or malformed."""
    count = (body or {}).get("hitCount")
    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


def _mirbase_url(source: Source, ident: str) -> str:
    # miRBase has no existence API, so a mature accession is checked against
    # RNAcentral through EBI Search, which indexes miRBase.
    return f"{_EBISEARCH_RNACENTRAL_BASE}?query={ident}&format=json"


def _mirbase_exists(status: int, body: dict | None) -> bool:
    if status != 200:
        raise RemoteError(f"EBI Search returned unexpected status {status}.")
    return _ebisearch_hitcount(body) >= 1


def _mirbase_cache_body(status: int, body: dict | None) -> dict | None:
    # Persist only the hit count, which is all existence needs.
    if status == 200:
        return {"hitCount": _ebisearch_hitcount(body)}
    return None


def _genenames_response(body: dict | None) -> dict:
    return (body or {}).get("response") or {}


def _genenames_approved(body: dict | None) -> bool:
    """Whether a genenames fetch resolved to an approved symbol."""
    resp = _genenames_response(body)
    try:
        found = int(resp.get("numFound") or 0)
    except (TypeError, ValueError):
        found = 0
    if found < 1:
        return False
    docs = resp.get("docs") or []
    return bool(docs) and str(docs[0].get("status")) == "Approved"


def _genenames_url(source: Source, ident: str) -> str:
    # The HGNC REST service answers JSON only through the Accept header, which the
    # transport sends for every request. A previous or withdrawn symbol is not an
    # approved symbol and so is absent here; cache mode carries the successor map.
    return f"{_GENENAMES_BASE}symbol/{ident}"


def _genenames_exists(status: int, body: dict | None) -> bool:
    # genenames answers 200 with numFound 0 for a symbol it does not know, so
    # existence is decided from the body rather than the status.
    if status == 200:
        return _genenames_approved(body)
    if status == 404:
        return False
    raise RemoteError(f"genenames.org returned unexpected status {status}.")


def _genenames_cache_body(status: int, body: dict | None) -> dict | None:
    # Persist only the count and the first doc's status, which is all existence
    # needs.
    if status == 200:
        resp = _genenames_response(body)
        docs = resp.get("docs") or []
        kept = [{"status": docs[0].get("status")}] if docs else []
        return {"response": {"numFound": resp.get("numFound"), "docs": kept}}
    return None


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
    subkey=lambda source: "entry",
    url=_pdb_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_CHEMBL = Resolver(
    name="chembl",
    subkey=lambda source: "lookup",
    url=_chembl_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_REACTOME = Resolver(
    name="reactome",
    subkey=lambda source: "query",
    url=_reactome_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_INTERPRO = Resolver(
    name="interpro",
    subkey=_interpro_subkey,
    url=_interpro_url,
    exists=_interpro_exists,
    cache_body=_interpro_cache_body,
    species_ok=_interpro_species_ok,
    retired=_interpro_retired,
)

_RFAM = Resolver(
    name="rfam",
    subkey=lambda source: "family",
    url=_rfam_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_UNIPARC = Resolver(
    name="uniparc",
    subkey=lambda source: "uniparc",
    url=_uniparc_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_COMPLEXPORTAL = Resolver(
    name="complexportal",
    subkey=lambda source: "complex",
    url=_complexportal_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_WIKIPATHWAYS = Resolver(
    name="wikipathways",
    subkey=lambda source: "pathways",
    url=_wikipathways_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_PROSITE = Resolver(
    name="prosite",
    subkey=lambda source: "entry",
    url=_prosite_url,
    exists=_exists_by_404,
    cache_body=_no_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_REFSEQ = Resolver(
    name="refseq",
    subkey=lambda source: "esummary",
    url=_refseq_url,
    exists=_refseq_exists,
    cache_body=_refseq_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_CLINVAR = Resolver(
    name="clinvar",
    subkey=lambda source: "esearch",
    url=_clinvar_url,
    exists=_clinvar_exists,
    cache_body=_clinvar_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_MIRBASE = Resolver(
    name="mirbase",
    subkey=lambda source: "rnacentral",
    url=_mirbase_url,
    exists=_mirbase_exists,
    cache_body=_mirbase_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_GENENAMES = Resolver(
    name="genenames",
    subkey=lambda source: "symbol",
    url=_genenames_url,
    exists=_genenames_exists,
    cache_body=_genenames_cache_body,
    species_ok=_species_agnostic,
    retired=_never_retired,
)

_RESOLVERS = {
    "ols": _OLS,
    "ensembl": _ENSEMBL,
    "uniprot": _UNIPROT,
    "mutalyzer": _MUTALYZER,
    "dbsnp": _DBSNP,
    "pdb": _PDB,
    "chembl": _CHEMBL,
    "reactome": _REACTOME,
    "interpro": _INTERPRO,
    "rfam": _RFAM,
    "uniparc": _UNIPARC,
    "complexportal": _COMPLEXPORTAL,
    "wikipathways": _WIKIPATHWAYS,
    "prosite": _PROSITE,
    "refseq": _REFSEQ,
    "clinvar": _CLINVAR,
    "mirbase": _MIRBASE,
    "genenames": _GENENAMES,
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
    on_error: str = "raise",
) -> tuple[bool | None, str | None, str | None, str | None]:
    """Return ``(valid, suggestion, fetched_at, error)`` for ``ident``.

    An id that exists, matches ``species``, and is not obsolete is valid with no
    suggestion. An id that exists but is obsolete is not valid and carries its
    successor as the suggestion. An id that is absent or belongs to another
    species is not valid with no suggestion. ``fetched_at`` is the UTC stamp of
    the response the verdict came from, whether freshly fetched or read from the
    cache, so a caller can report when the check actually happened.

    The cache is keyed by id only; species is compared at read time against the
    cached body, so one cached response answers any species. ``refresh`` skips
    the cache and refetches; a cached response older than ``BIOGATE_REMOTE_TTL``
    seconds is refetched too. An indeterminate status or an exhausted-retry
    network failure raises before the cache is written, so a response that gives
    no definite answer is never persisted. When ``on_error`` is
    ``"indeterminate"`` that failure is caught and returned as
    ``(None, None, <stamp>, <message>)`` instead, so one unreachable id does not
    unwind the whole batch.
    """
    path = _remote_cache_path(resolver.name, resolver.subkey(source), ident)
    if not refresh and path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            status, body = cached["status"], cached.get("body")
            fetched_at = cached.get("fetched_at")
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # A corrupt or partial cache file is ignored and refetched.
        else:
            if not _is_stale(fetched_at, _remote_ttl()):
                if not resolver.exists(status, body):
                    return False, None, fetched_at, None
                valid, successor = _post_existence(
                    resolver, source, ident, body, species
                )
                return valid, successor, fetched_at, None
    url = resolver.url(source, ident)
    try:
        status, body = _http_get(url)
        result = resolver.exists(status, body)
    except RemoteError as error:
        if on_error != "indeterminate":
            raise
        # An unreachable or undecidable id is left indeterminate, not cached.
        return None, None, _utc_stamp(), str(error)
    fetched_at = _utc_stamp()
    _atomic_write_text(
        path,
        json.dumps(
            {
                "status": status,
                "body": resolver.cache_body(status, body),
                "url": url,
                "fetched_at": fetched_at,
            }
        ),
    )
    if not result:
        return False, None, fetched_at, None
    valid, successor = _post_existence(resolver, source, ident, body, species)
    return valid, successor, fetched_at, None


def _get_resolver(source: Source) -> Resolver:
    """Return the resolver for a source or raise ``NoResolverError``."""
    remote = source.remote
    if not remote or remote.get("resolver") not in _RESOLVERS:
        raise NoResolverError(f"No remote resolver for {source.key!r}.")
    return _RESOLVERS[remote["resolver"]]


def _max_workers() -> int:
    """Concurrent remote lookups, from ``BIOGATE_REMOTE_WORKERS`` (default 1).

    One means sequential, which keeps the offline test suite and the conformance
    corpus deterministic. A larger value checks a big column faster; per-host
    politeness still applies through the rate limiter.
    """
    raw = os.environ.get("BIOGATE_REMOTE_WORKERS")
    if not raw:
        return 1
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


_PROGRESS_MIN = 50  # only show progress for a batch at least this large


class _NullProgress:
    def update(self, n: int = 1) -> None:
        pass

    def close(self) -> None:
        pass


class _StderrProgress:
    """A minimal fallback progress counter on stderr when tqdm is absent."""

    def __init__(self, total: int) -> None:
        self._total = total
        self._done = 0

    def update(self, n: int = 1) -> None:
        self._done += n
        print(
            f"\rbiogate: checked {self._done}/{self._total}",
            end="",
            file=sys.stderr,
            flush=True,
        )

    def close(self) -> None:
        print("", file=sys.stderr)


def _make_progress(total: int, enabled: bool):
    """A progress reporter for a large concurrent batch, else a no-op.

    Nothing is shown for a small batch, a sequential run, or a non-interactive
    stderr, so scripts and the test suite stay silent. tqdm is used when it is
    importable; otherwise a plain stderr counter is.
    """
    if not enabled or total < _PROGRESS_MIN or not sys.stderr.isatty():
        return _NullProgress()
    try:
        from tqdm import tqdm
    except ModuleNotFoundError:  # pragma: no cover - optional, interactive only
        return _StderrProgress(total)
    return tqdm(total=total, desc="biogate remote", unit="id")  # pragma: no cover


def _resolve_ids(
    resolver: Resolver,
    source: Source,
    ids: list[str],
    species,
    refresh: bool = False,
    on_error: str = "raise",
) -> dict[str, tuple[bool | None, str | None, str | None, str | None]]:
    """Resolve each id to ``(valid, successor, fetched_at, error)``.

    Sequential by default. With ``BIOGATE_REMOTE_WORKERS`` above one, the lookups
    run on a bounded thread pool: the work is I/O-bound, the verdict logic is pure
    and per-id, and each id writes its own cache file, so concurrency only reorders
    the network and never changes a verdict. The returned mapping is keyed by id,
    so input order is restored by the caller regardless of completion order.
    """
    workers = _max_workers()
    if workers == 1 or len(ids) <= 1:
        return {
            ident: _remote_lookup(resolver, source, ident, species, refresh, on_error)
            for ident in ids
        }
    results: dict[str, tuple[bool | None, str | None, str | None, str | None]] = {}
    progress = _make_progress(len(ids), enabled=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _remote_lookup, resolver, source, ident, species, refresh, on_error
            ): ident
            for ident in ids
        }
        try:
            for future in concurrent.futures.as_completed(futures):
                results[futures[future]] = future.result()
                progress.update(1)
        finally:
            progress.close()
    return results


def remote_verdicts(
    source: Source,
    items: list[str],
    species=None,
    refresh: bool = False,
    on_error: str = "raise",
) -> list[tuple[bool | None, str | None, str | None, str | None, str | None]]:
    """Return ``(valid, normalized, suggestion, fetched_at, error)`` per item.

    Well-formed inputs are looked up directly; one that exists but is obsolete is
    not valid and carries its successor as the suggestion. Malformed inputs offer
    a suggestion only when a correction candidate exists remotely. When
    ``species`` is given, an id that exists but belongs to a different species is
    not valid. ``fetched_at`` is the UTC stamp of the response the id's verdict
    came from, or None for a missing input or one that was never fetched.
    ``refresh`` skips any cached response and refetches. Existence is resolved for
    the whole batch in a single resolver call. Under ``on_error="indeterminate"``
    a well-formed id whose lookup could not complete is ``valid=None`` with the
    failure message in ``error``; a malformed input stays invalid regardless.
    """
    resolver = _get_resolver(source)
    plans: list[tuple[bool | None, str | None]] = []
    need: set[str] = set()
    for item in items:
        if item is None:
            plans.append((None, None))
            continue
        if matches(source.pattern, item):
            plans.append((True, item))
            need.add(item)
        else:
            candidate = _suggest(source, item)
            plans.append((False, candidate))
            if candidate is not None:
                need.add(candidate)
    resolved = (
        _resolve_ids(resolver, source, sorted(need), species, refresh, on_error)
        if need
        else {}
    )
    verdicts: list[tuple[bool | None, str | None, str | None, str | None, str | None]]
    verdicts = []
    for well_formed, value in plans:
        if well_formed is None:
            verdicts.append((None, None, None, None, None))
            continue
        valid, successor, fetched_at, error = resolved.get(
            value, (False, None, None, None)
        )
        if well_formed:
            if error is not None:
                # The id's own lookup could not be determined.
                verdicts.append((None, None, None, fetched_at, error))
            elif valid:
                verdicts.append((True, value, None, fetched_at, None))
            else:
                verdicts.append((False, None, successor, fetched_at, None))
        # A malformed input is invalid regardless; only offer a suggestion when
        # the correction candidate was confirmed to exist.
        elif value is not None and valid:
            verdicts.append((False, None, value, fetched_at, None))
        else:
            verdicts.append((False, None, None, fetched_at, None))
    return verdicts
