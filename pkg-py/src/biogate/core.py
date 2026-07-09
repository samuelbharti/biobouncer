"""Public entry points: check_id and is_valid_id."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from ._cache import (
    MissingVersionError,
    _ids_from_text,
    _snapshot_text,
    cache_check,
    snapshot_set,
)
from ._pattern import check_one
from ._registry import get_source
from ._remote import remote_verdicts
from ._result import Result

_KNOWN_MODES = ("pattern", "cache", "remote", "existence")


def _is_scalar(x: object) -> bool:
    return isinstance(x, str) or not isinstance(x, Iterable)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
            live existence against the source API; "existence" uses a pinned
            snapshot when one is available for ``version`` and otherwise falls
            back to "remote".
        species: Optional species context, echoed in the result.
        version: Optional version context. Ignored in pattern mode.

    Returns:
        A list of ``Result``, one per input, in the input order.
    """
    if how not in _KNOWN_MODES:
        raise ValueError(
            f"Invalid mode how={how!r}. Choose one of {', '.join(_KNOWN_MODES)}."
        )
    source = get_source(source_db)
    items = [str(it) for it in ([x] if _is_scalar(x) else list(x))]

    # Resolve where verdicts come from. ``ids`` drives the offline snapshot path
    # (cache, or existence when a snapshot is available); ``remote_out`` drives
    # the live path (remote, or existence with no usable snapshot); neither means
    # pure pattern.
    ids = None
    remote_out = None
    result_version = None

    if how == "cache":
        if version is None:
            raise MissingVersionError(
                f"version is required for cache mode (source {source_db!r})."
            )
        version = str(version)
        ids = snapshot_set(source_db, version)
        result_version = version
    elif how == "remote":
        remote_out = remote_verdicts(source, items)
        result_version = _utc_stamp()
    elif how == "existence":
        # Cache-then-remote fallback: answer from a pinned snapshot when one is
        # available for the requested version, otherwise check live.
        snapshot = None
        if version is not None:
            version = str(version)
            text = _snapshot_text(source_db, version)
            if text is not None:
                snapshot = _ids_from_text(text)
        if snapshot is not None:
            ids = snapshot
            result_version = version
        else:
            remote_out = remote_verdicts(source, items)
            result_version = _utc_stamp()

    results = []
    for idx, s in enumerate(items):
        if ids is not None:
            valid, normalized, suggestion = cache_check(source, s, ids)
        elif remote_out is not None:
            valid, normalized, suggestion = remote_out[idx]
        else:
            valid, normalized, suggestion = check_one(source, s, species)
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
