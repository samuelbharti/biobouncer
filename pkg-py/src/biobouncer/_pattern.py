"""Pattern mode: offline, deterministic checks against a source regex.

The regexes live in the shared spec and use ASCII classes so that R (PCRE) and
Python agree element for element.
"""

from __future__ import annotations

import functools
import re

from ._registry import Source

_LOCAL_DIGITS = re.compile("[0-9]+")

# ENS, a greedy species code, one feature letter, then 11 digits. The greedy
# [A-Z]* plus the single [EFGPT] yields "" for ENSG... and "MUS" for ENSMUSG...
_ENSEMBL_ID = re.compile("^ENS([A-Z]*)[EFGPT][0-9]{11}$")


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


def _ensembl_id_prefix(ident: str) -> str | None:
    """Return the species code between ENS and the feature letter.

    Returns "" for a human id (ENSG...), the code for other species (for
    example "MUS" for ENSMUSG...), or None when ``ident`` is not an Ensembl
    stable id.
    """
    m = _ENSEMBL_ID.match(ident)
    if m is None:
        return None
    return m.group(1)


def _ensembl_species_prefix(species_block: dict, species) -> str | None:
    """Return the expected id prefix for ``species`` from the species map.

    ``species`` may be a name like "homo_sapiens" or a taxon id like 9606.
    Returns the mapped prefix (which may be "") or None when the species is
    not in the map.
    """
    for entry in species_block.get("map", []):
        if str(entry.get("name")) == str(species) or entry.get("taxon") == species:
            return entry.get("prefix")
    return None


def _species_ok(source: Source, ident: str, species) -> bool:
    """Whether ``ident`` is consistent with the requested ``species``.

    Lenient: a missing species, a source without a species scheme we know, or
    a species outside the map all pass. A non-Ensembl-shaped id also passes;
    the base pattern decides shape.
    """
    if species is None:
        return True
    block = source.species
    if not block or block.get("scheme") != "ensembl_prefix":
        return True
    expected = _ensembl_species_prefix(block, species)
    if expected is None:
        return True
    id_prefix = _ensembl_id_prefix(ident)
    if id_prefix is None:
        return True
    return id_prefix == expected


def check_one(
    source: Source, s: str, species=None
) -> tuple[bool, str | None, str | None]:
    """Return ``(valid, normalized, suggestion)`` for a single input."""
    if matches(source.pattern, s):
        if _species_ok(source, s, species):
            return True, s, None
        return False, None, None
    candidate = _suggest(source, s)
    if candidate is not None and _species_ok(source, candidate, species):
        return False, None, candidate
    return False, None, None
