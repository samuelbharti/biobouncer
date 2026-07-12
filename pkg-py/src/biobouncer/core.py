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
    default_cache_version,
    snapshot_set,
)
from ._fuzzy import fuzzy_index
from ._pattern import check_one
from ._registry import get_source
from ._remote import _utc_stamp, remote_verdicts
from ._result import Result

_KNOWN_MODES = ("pattern", "cache", "remote", "existence")
_ON_ERROR = ("raise", "indeterminate")


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
    on_error: str = "raise",
) -> list[Result]:
    """Check one or more identifiers against a source.

    Args:
        x: A string or an iterable of strings.
        source_db: Source key, for example "mondo". See ``sources()``.
        how: Checking mode. "pattern" and "cache" run offline; "remote" checks
            live existence against the source API; "existence" uses a pinned
            snapshot when one is available for ``version``, otherwise falls back
            to "remote", and for a source with no resolver falls back to
            "pattern".
        species: Optional species context, echoed in the result.
        version: Optional version context. In cache mode it selects the snapshot
            and defaults to the latest installed one when omitted; in existence
            mode it selects a snapshot when available. Ignored in pattern mode.
        refresh: In remote checks, skip any cached response and refetch. Ignored
            by the offline modes.
        on_error: How a per-id remote failure is handled. "raise" (the default)
            lets the failure unwind the whole call. "indeterminate" leaves just
            that id ``valid=None`` with the reason in its ``error`` field and
            checks the rest of the batch, so one unreachable id does not lose the
            others. Ignored by the offline modes.

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
    if on_error not in _ON_ERROR:
        raise ValueError(
            f"Invalid on_error={on_error!r}. Choose one of {', '.join(_ON_ERROR)}."
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
            # Default to the latest installed snapshot rather than forcing the
            # caller to name a version. Only raise when nothing is installed.
            version = default_cache_version(source_db, source)
            if version is None:
                raise MissingVersionError(
                    f"No snapshot is installed for {source_db!r} to default to. "
                    f"Pass a version or run biobouncer.pull({source_db!r})."
                )
        else:
            version = str(version)
        ids = snapshot_set(source_db, version)
        retired = _snapshot_retired(source_db, version)
        result_version = version
    elif how == "remote":
        remote_out = remote_verdicts(source, items, species, refresh, on_error)
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
        elif source.remote:
            remote_out = remote_verdicts(source, items, species, refresh, on_error)
            result_version = _utc_stamp()
        # else: no snapshot and no resolver. Fall through to the pattern path
        # below, so existence degrades to a shape check rather than raising, which
        # honors existence mode's graceful-fallback story for pattern-only sources.

    # A source may offer fuzzy suggestions in the offline snapshot path. Build the
    # length index once for the whole batch, not per input.
    fuzzy = None
    if ids is not None and source.suggest:
        fuzzy_cfg = source.suggest.get("fuzzy")
        if fuzzy_cfg:
            fuzzy = (fuzzy_index(ids), int(fuzzy_cfg["max_distance"]))

    results = []
    for idx, s in enumerate(items):
        version = result_version
        error = None
        if s is None:
            valid, normalized, suggestion = None, None, None
        elif ids is not None:
            valid, normalized, suggestion = cache_check(source, s, ids, retired, fuzzy)
        elif remote_out is not None:
            valid, normalized, suggestion, fetched_at, error = remote_out[idx]
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
                error=error,
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
) -> bool | None | list[bool | None]:
    """Return just the validity verdict.

    Returns a single verdict for a scalar input, or a list of verdicts for an
    iterable, matching the shape of ``x``. A verdict is ``True`` (valid),
    ``False`` (invalid), or ``None`` for a missing input (``None``, a float
    ``NaN``, or pandas ``NA``). A missing input is deliberately not ``False``, so
    callers can tell "absent" apart from "present but wrong".
    """
    results = check_id(
        x, source_db, how=how, species=species, version=version, refresh=refresh
    )
    if _is_scalar(x):
        return results[0].valid
    return [r.valid for r in results]
