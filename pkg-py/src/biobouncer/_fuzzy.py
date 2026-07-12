"""Fuzzy "did you mean" suggestions by bounded edit distance.

A pure, deterministic Levenshtein used only in cache and existence modes, where a
local set of valid ids is available. It is specified exactly so R and Python make
the identical suggestion: bounded edit distance with unit costs, ties broken by
the code-point-smallest candidate.
"""

from __future__ import annotations


def _bounded_levenshtein(a: str, b: str, k: int) -> int | None:
    """The Levenshtein distance between ``a`` and ``b`` if it is at most ``k``.

    Returns ``None`` when the distance exceeds ``k``. Unit insertion, deletion,
    and substitution costs, no transposition, case sensitive. A running row
    minimum stops the search early once every path already exceeds ``k``.
    """
    la, lb = len(a), len(b)
    if abs(la - lb) > k:
        return None
    previous = list(range(lb + 1))
    for i in range(1, la + 1):
        current = [i] + [0] * lb
        row_min = i
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost
            )
            if current[j] < row_min:
                row_min = current[j]
        if row_min > k:
            return None
        previous = current
    distance = previous[lb]
    return distance if distance <= k else None


def fuzzy_index(ids) -> dict[int, list[str]]:
    """Bucket candidate ids by length so the search can prune by length."""
    buckets: dict[int, list[str]] = {}
    for candidate in ids:
        buckets.setdefault(len(candidate), []).append(candidate)
    return buckets


def fuzzy_suggest(s: str, index: dict[int, list[str]], k: int) -> str | None:
    """The nearest candidate within edit distance ``k``, or ``None``.

    Only candidates whose length is within ``k`` of ``s`` can be within distance
    ``k``, so the search visits just those length buckets. Among the candidates at
    the smallest distance, the code-point-smallest is chosen, so R and Python
    always agree.
    """
    best: str | None = None
    best_distance = k + 1
    length = len(s)
    for candidate_length in range(length - k, length + k + 1):
        for candidate in index.get(candidate_length, ()):
            distance = _bounded_levenshtein(s, candidate, k)
            if distance is None:
                continue
            if distance < best_distance or (
                distance == best_distance and candidate < best
            ):
                best_distance = distance
                best = candidate
    return best
