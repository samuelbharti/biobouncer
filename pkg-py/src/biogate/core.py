"""Public entry points: check_id and is_valid_id."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from ._cache import MissingVersionError, cache_check, snapshot_set
from ._pattern import check_one
from ._registry import get_source
from ._remote import remote_verdicts
from ._result import Result

_KNOWN_MODES = ("pattern", "cache", "remote", "existence")
_MODES = ("pattern", "cache", "remote")


def _is_scalar(x: object) -> bool:
    return isinstance(x, str) or not isinstance(x, Iterable)


def check_id(
    x,
    source_db: str,
    how: str = "pattern",
    species: str | None = None,
    version: str | None = None,
) -> list[Result]:
    """Check one or more identifiers against a source.

    Args:
        x: A string or an iterable of strings.
        source_db: Source key, for example "mondo". See ``sources()``.
        how: Checking mode. "pattern" and "cache" run offline; "remote" checks
            live existence against the source API.
        species: Optional species context, echoed in the result.
        version: Optional version context. Ignored in pattern mode.

    Returns:
        A list of ``Result``, one per input, in the input order.
    """
    if how not in _KNOWN_MODES:
        raise ValueError(
            f"Invalid mode how={how!r}. Choose one of {', '.join(_KNOWN_MODES)}."
        )
    if how not in _MODES:
        raise ValueError(
            f"Mode {how!r} is not implemented yet. "
            f"Implemented modes: {', '.join(_MODES)}."
        )
    source = get_source(source_db)
    items = [x] if _is_scalar(x) else list(x)

    if how == "cache":
        if version is None:
            raise MissingVersionError(
                f"version is required for cache mode (source {source_db!r})."
            )
        version = str(version)
        ids = snapshot_set(source_db, version)

    if how == "remote":
        remote_out = remote_verdicts(source, [str(it) for it in items])
        version_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []
    for idx, item in enumerate(items):
        s = str(item)
        if how == "cache":
            valid, normalized, suggestion = cache_check(source, s, ids)
            result_version = version
        elif how == "remote":
            valid, normalized, suggestion = remote_out[idx]
            result_version = version_stamp
        else:
            valid, normalized, suggestion = check_one(source, s)
            result_version = None
        results.append(
            Result(
                input=s,
                valid=valid,
                normalized=normalized,
                suggestion=suggestion,
                source_db=source_db,
                version=result_version,
                species=species,
                how=how,
            )
        )
    return results


def is_valid_id(
    x,
    source_db: str,
    how: str = "pattern",
    species: str | None = None,
    version: str | None = None,
):
    """Return just the validity verdict.

    Returns a single bool for a scalar input, or a list of bool for an iterable,
    matching the shape of ``x``.
    """
    results = check_id(x, source_db, how=how, species=species, version=version)
    if _is_scalar(x):
        return results[0].valid
    return [r.valid for r in results]
