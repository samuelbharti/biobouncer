"""Pattern mode: offline, deterministic checks against a source regex.

The regexes live in the shared spec and use ASCII classes so that R (PCRE) and
Python agree element for element.
"""

from __future__ import annotations

import functools
import re

from ._registry import Source

_LOCAL_DIGITS = re.compile("[0-9]+")


@functools.lru_cache(maxsize=256)
def _compiled(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def matches(pattern: str, s: str) -> bool:
    """Whether ``s`` matches ``pattern`` in full."""
    return _compiled(pattern).fullmatch(s) is not None


def _suggest(source: Source, s: str) -> str | None:
    curie = source.curie
    if curie:
        prefix = curie["prefix"]
        pad_to = curie.get("pad_to")
        head, sep, local = s.partition(":")
        if not sep:
            head, local = prefix, s
        if head.upper() != prefix.upper():
            return None
        if pad_to and _LOCAL_DIGITS.fullmatch(local):
            local = local.zfill(int(pad_to))
        candidate = f"{prefix}:{local}"
        if candidate != s and matches(source.pattern, candidate):
            return candidate
        return None

    norm = source.normalize
    if norm and norm.get("case") in ("upper", "lower"):
        candidate = s.upper() if norm["case"] == "upper" else s.lower()
        if candidate != s and matches(source.pattern, candidate):
            return candidate
    return None


def check_one(source: Source, s: str) -> tuple[bool, str | None, str | None]:
    """Return ``(valid, normalized, suggestion)`` for a single input."""
    if matches(source.pattern, s):
        return True, s, None
    return False, None, _suggest(source, s)
