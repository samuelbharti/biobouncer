"""Remote mode: live existence checks against a source API.

The only resolver so far is OLS (EBI Ontology Lookup Service), which covers the
ontology sources mondo, efo, go, and chebi. Remote mode mirrors cache mode, with
membership in a pinned snapshot replaced by live existence via the resolver.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from ._cache import cache_dir
from ._pattern import _suggest, matches
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


def _remote_cache_path(onto: str, ident: str) -> Path:
    """On-disk path for a cached remote response."""
    return cache_dir() / "remote" / "ols" / onto / f"{ident.replace(':', '_')}.json"


def _ols_count(body: dict | None) -> int:
    """The matching-term count in an OLS response, 0 when absent or malformed."""
    page = (body or {}).get("page") or {}
    total = page.get("totalElements") or 0
    try:
        return int(total)
    except (TypeError, ValueError):
        return 0


def _ols_request(
    onto: str, ident: str, refresh: bool = False
) -> tuple[int, dict | None]:
    """Return ``(status, body)`` for a term, backed by an on-disk response cache."""
    path = _remote_cache_path(onto, ident)
    if not refresh and path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            return cached["status"], cached.get("body")
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # A corrupt or partial cache file is ignored and refetched.
    url = f"{_OLS_BASE}/ontologies/{onto}/terms?obo_id={ident}"
    status, body = _http_get(url)
    if status in (200, 404):
        stored = (
            {"page": {"totalElements": _ols_count(body)}} if status == 200 else None
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"status": status, "body": stored, "url": url}),
            encoding="utf-8",
        )
    return status, body


def _ols_exists(onto: str, ident: str) -> bool:
    """Whether ``ident`` exists in ``onto`` via the OLS resolver."""
    status, body = _ols_request(onto, ident)
    if status == 200:
        return _ols_count(body) >= 1
    if status == 404:
        return False
    raise RemoteError(f"Unexpected status {status} for {ident!r} in {onto!r}.")


def _ols_resolver(source: Source, ids: list[str]) -> dict[str, bool]:
    """Resolve existence for a batch of ids in one ontology."""
    onto = source.remote["ols_ontology"]
    return {ident: _ols_exists(onto, ident) for ident in ids}


_RESOLVERS = {"ols": _ols_resolver}


def _get_resolver(source: Source):
    """Return the resolver callable for a source or raise ``NoResolverError``."""
    remote = source.remote
    if not remote or remote.get("resolver") not in _RESOLVERS:
        raise NoResolverError(f"No remote resolver for {source.key!r}.")
    return _RESOLVERS[remote["resolver"]]


def remote_verdicts(
    source: Source, items: list[str]
) -> list[tuple[bool, str | None, str | None]]:
    """Return ``(valid, normalized, suggestion)`` per item via live existence.

    Well-formed inputs are looked up directly. Malformed inputs offer a
    suggestion only when a correction candidate exists remotely. Existence is
    resolved for the whole batch in a single resolver call.
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
    exists = resolver(source, sorted(need)) if need else {}
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
