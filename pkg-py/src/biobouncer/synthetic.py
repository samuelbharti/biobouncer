"""Generate a synthetic, labeled column of identifiers for any source.

``synthesize`` builds a small "messy column" for a source: a mix of well-formed
ids, repairable ids (a wrong-case or unpadded form that suggests a valid one),
hard-invalid ids, and missing cells. Every value is labeled by running the
pattern-mode checker itself, so the labels are always correct and match what the R
``synthesize_ids`` produces for the same source.

It is useful for exercising a validation pipeline (feed the column to ``report``,
``repair``, or an adapter) and for teaching, without hand-writing test data. The
generation is deterministic and offline: the same arguments always produce the
same column, in both languages.
"""

from __future__ import annotations

import re

from ._registry import Source, get_source
from .core import check_id

_DIGIT_RUN = re.compile("[0-9]+")

# The four disjoint categories a cell can fall into, in the order they are woven
# into the returned column.
_CATEGORIES = ("valid", "repairable", "invalid", "missing")

# Characters guaranteed to be outside every source pattern, used to turn a valid
# id into a hard invalid (one that neither matches nor is suggestible).
_BREAKERS = ("!", " x", "##")


def _increment_last_digit_run(s: str, delta: int) -> str | None:
    """Return ``s`` with its last run of digits increased by ``delta``.

    The run keeps its original width by zero-padding, so ``MONDO:0005148`` with
    ``delta=1`` becomes ``MONDO:0005149``. Returns ``None`` when there is no digit
    run (for example an InChIKey) or the result would go negative.
    """
    runs = list(_DIGIT_RUN.finditer(s))
    if not runs:
        return None
    run = runs[-1]
    value = int(run.group()) + delta
    if value < 0:
        return None
    replacement = str(value).zfill(len(run.group()))
    return s[: run.start()] + replacement + s[run.end() :]


def _valid_values(source: Source, n: int, seed: int) -> list[str]:
    """Up to ``n`` well-formed ids: the example plus deterministic increments."""
    values = [source.example]
    for i in range(1, n):
        candidate = _increment_last_digit_run(source.example, i + seed)
        if candidate is not None and candidate not in values:
            values.append(candidate)
    return values


def _repairable_values(source: Source) -> list[str]:
    """Denormalized forms of the example that should suggest a valid id.

    Inverts the pattern-mode suggestion rules: for a CURIE source, lowercase the
    prefix and (when the local part is zero-padded) drop the padding; for a
    ``normalize`` source, flip the case. Empty for a source with neither, which
    has no pattern-mode repairable form.
    """
    example = source.example
    candidates: list[str] = []
    if source.curie:
        head, sep, local = example.partition(":")
        if sep and head.lower() != head:
            candidates.append(f"{head.lower()}:{local}")
        if source.curie.get("pad_to") and local.isdigit():
            stripped = local.lstrip("0") or "0"
            if stripped != local:
                candidates.append(f"{head}:{stripped}")
        return candidates

    norm = source.normalize
    case = norm.get("case") if norm else None
    if case == "upper" and example.lower() != example:
        candidates.append(example.lower())
    elif case == "lower" and example.upper() != example:
        candidates.append(example.upper())
    return candidates


def _invalid_values(source: Source, n: int) -> list[str]:
    """Up to ``n`` hard-invalid ids: the example with a breaker appended."""
    return [f"{source.example}{breaker}" for breaker in _BREAKERS[:n]]


def _categorize(result) -> str:
    if result.valid is True:
        return "valid"
    if result.valid is None:
        return "missing"
    if result.suggestion is not None:
        return "repairable"
    return "invalid"


def _row(source_db: str, value: str | None) -> dict:
    result = check_id([value], source_db, how="pattern")[0]
    return {
        "input": result.input,
        "category": _categorize(result),
        "valid": result.valid,
        "normalized": result.normalized,
        "suggestion": result.suggestion,
    }


def _rows_for(source_db: str, values, target: str, limit: int) -> list[dict]:
    """Label ``values`` and keep up to ``limit`` that land in ``target``."""
    rows = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        row = _row(source_db, value)
        if row["category"] == target:
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def _interleave(buckets: dict[str, list[dict]]) -> list[dict]:
    """Weave the category buckets together so the column reads as mixed."""
    ordered = [buckets[category] for category in _CATEGORIES]
    out: list[dict] = []
    depth = max((len(bucket) for bucket in ordered), default=0)
    for i in range(depth):
        for bucket in ordered:
            if i < len(bucket):
                out.append(bucket[i])
    return out


def synthesize(
    source_db: str,
    n_valid: int = 2,
    n_repairable: int = 1,
    n_invalid: int = 1,
    missing: int = 1,
    seed: int = 0,
) -> list[dict]:
    """Build a synthetic, labeled column of ids for one source.

    Args:
        source_db: Source key, for example ``"mondo"``. See ``sources()``.
        n_valid: How many well-formed ids to include (the example plus
            deterministic variants). A source with no numeric part yields just
            the example.
        n_repairable: How many repairable ids (a wrong-case or unpadded form that
            suggests a valid id). ``ec``, ``hgvs``, and ``hgnc`` have no
            pattern-mode repairable form, so they yield none.
        n_invalid: How many hard-invalid ids (neither valid nor suggestible).
        missing: How many missing cells (``None``).
        seed: Shifts the numeric variants, for a different but still deterministic
            column.

    Returns:
        A list of row dicts, woven so the categories are interleaved. Each row has
        ``input``, ``category`` (``"valid"``, ``"repairable"``, ``"invalid"``, or
        ``"missing"``), and the pattern-mode ``valid``, ``normalized``, and
        ``suggestion`` for that input. Categories a source cannot produce are
        simply absent.
    """
    source = get_source(source_db)
    buckets = {
        "valid": _rows_for(
            source_db, _valid_values(source, n_valid, seed), "valid", n_valid
        ),
        "repairable": _rows_for(
            source_db, _repairable_values(source), "repairable", n_repairable
        ),
        "invalid": _rows_for(
            source_db, _invalid_values(source, len(_BREAKERS)), "invalid", n_invalid
        ),
        "missing": _rows_for(source_db, [None] * missing, "missing", missing),
    }
    return _interleave(buckets)
