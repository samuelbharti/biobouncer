"""Public entry points: check_id and is_valid_id."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from ._cache import (
    MissingVersionError,
    _ids_from_text,
    _snapshot_retired,
    _snapshot_text,
    cache_check,
    snapshot_set,
)
from ._pattern import check_one
from ._registry import get_source
from ._remote import _utc_stamp, remote_verdicts
from ._result import Result

_KNOWN_MODES = ("pattern", "cache", "remote", "existence")


class InvalidModeError(ValueError):
    """Raised when ``how`` is not one of the supported checking modes."""


def _is_scalar(x: object) -> bool:
    return isinstance(x, str) or not isinstance(x, Iterable)


def _is_missing(value: object) -> bool:
    """Whether a value is missing rather than an identifier to check.

    Covers ``None``, a float ``NaN`` (including ``numpy.nan``, which is a float),
    and pandas ``NA``, so a missing cell propagates as ``valid=None`` instead of
    being checked as the literal string ``"None"`` or ``"nan"``.
    """
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return type(value).__name__ in ("NAType", "NaTType")


def check_id(
    x: str | Iterable[str],
    source_db: str,
    how: str = "pattern",
    species: str | None = None,
    version: str | None = None,
    refresh: bool = False,
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
        refresh: In remote checks, skip any cached response and refetch. Ignored
            by the offline modes.

    Returns:
        A list of ``Result``, one per input, in the input order.
    """
    if not isinstance(source_db, str):
        raise TypeError(f"source_db must be a string, got {type(source_db).__name__}.")
    if not isinstance(how, str):
        raise TypeError(f"how must be a string, got {type(how).__name__}.")
    if isinstance(x, (bytes, bytearray, Mapping)):
        raise TypeError(
            f"x must be a string or an iterable of strings, got {type(x).__name__}."
        )
    if how not in _KNOWN_MODES:
        raise InvalidModeError(
            f"Invalid mode how={how!r}. Choose one of {', '.join(_KNOWN_MODES)}."
        )
    source = get_source(source_db)
    raw = [x] if _is_scalar(x) else list(x)
    items = [None if _is_missing(it) else str(it) for it in raw]

    # Resolve where verdicts come from. ``ids`` drives the offline snapshot path
    # (cache, or existence when a snapshot is available); ``remote_out`` drives
    # the live path (remote, or existence with no usable snapshot); neither means
    # pure pattern.
    ids = None
    retired = {}
    remote_out = None
    result_version = None

    if how == "cache":
        if version is None:
            raise MissingVersionError(
                f"version is required for cache mode (source {source_db!r})."
            )
        version = str(version)
        ids = snapshot_set(source_db, version)
        retired = _snapshot_retired(source_db, version)
        result_version = version
    elif how == "remote":
        remote_out = remote_verdicts(source, items, species, refresh)
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
            retired = _snapshot_retired(source_db, version)
            result_version = version
        else:
            remote_out = remote_verdicts(source, items, species, refresh)
            result_version = _utc_stamp()

    results = []
    for idx, s in enumerate(items):
        version = result_version
        if s is None:
            valid, normalized, suggestion = None, None, None
        elif ids is not None:
            valid, normalized, suggestion = cache_check(source, s, ids, retired)
        elif remote_out is not None:
            valid, normalized, suggestion, fetched_at = remote_out[idx]
            if fetched_at is not None:
                version = fetched_at
        else:
            valid, normalized, suggestion = check_one(source, s, species)
        results.append(
            Result(
                input=s,
                valid=valid,
                normalized=normalized,
                suggestion=suggestion,
                source_db=source_db,
                version=version,
                species=species,
                how=how,
            )
        )
    return results


def is_valid_id(
    x: str | Iterable[str],
    source_db: str,
    how: str = "pattern",
    species: str | None = None,
    version: str | None = None,
    refresh: bool = False,
) -> bool | list[bool]:
    """Return just the validity verdict.

    Returns a single bool for a scalar input, or a list of bool for an iterable,
    matching the shape of ``x``.
    """
    results = check_id(
        x, source_db, how=how, species=species, version=version, refresh=refresh
    )
    if _is_scalar(x):
        return results[0].valid
    return [r.valid for r in results]
