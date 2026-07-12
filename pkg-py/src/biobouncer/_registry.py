"""Load source definitions from the vendored shared spec."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib.resources import files

import yaml


class UnknownSourceError(ValueError):
    """Raised when a source key is not in the registry."""


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    description: str
    pattern: str
    species_aware: bool
    version_aware: bool
    curie: dict | None
    normalize: dict | None
    cache: dict | None
    remote: dict | None
    species: dict | None = None
    example: str | None = None
    default_version: str | None = None
    suggest: dict | None = None

    def modes(self) -> list[str]:
        """Return the checking modes this source supports, in order."""
        out = ["pattern"]
        if self.cache:
            out.append("cache")
        if self.remote:
            out.append("remote")
        return out


@functools.lru_cache(maxsize=1)
def _registry() -> dict[str, Source]:
    root = files("biobouncer") / "_data" / "sources"
    out: dict[str, Source] = {}
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not entry.name.endswith(".yaml"):
            continue
        spec = yaml.safe_load(entry.read_text(encoding="utf-8"))
        out[spec["key"]] = Source(
            key=spec["key"],
            name=spec.get("name", spec["key"]),
            description=spec.get("description", ""),
            pattern=spec["pattern"],
            species_aware=bool(spec.get("species_aware", False)),
            version_aware=bool(spec.get("version_aware", False)),
            curie=spec.get("curie"),
            normalize=spec.get("normalize"),
            cache=spec.get("cache"),
            remote=spec.get("remote"),
            species=spec.get("species"),
            example=spec.get("example"),
            default_version=spec.get("default_version"),
            suggest=spec.get("suggest"),
        )
    return out


def sources() -> list[str]:
    """Return the sorted list of available source keys."""
    return sorted(_registry())


def source_info() -> list[dict]:
    """Describe every source, one dict per source, sorted by key.

    Each dict answers "what does a valid id look like and how can I check it?".

    Returns:
        A list of dicts with keys ``key``, ``name``, ``example`` (a valid
        identifier for the source), ``modes`` (the checking modes it supports),
        ``species_aware``, and ``version_aware``.

    Example:
        >>> import biobouncer as bg
        >>> info = {row["key"]: row for row in bg.source_info()}
        >>> info["mondo"]["example"]
        'MONDO:0005148'
        >>> info["mondo"]["modes"]
        ['pattern', 'cache', 'remote']
    """
    reg = _registry()
    return [
        {
            "key": src.key,
            "name": src.name,
            "example": src.example,
            "modes": src.modes(),
            "species_aware": src.species_aware,
            "version_aware": src.version_aware,
        }
        for src in (reg[k] for k in sorted(reg))
    ]


def get_source(key: str) -> Source:
    """Return the Source for ``key`` or raise ValueError if it is unknown."""
    reg = _registry()
    if key not in reg:
        raise UnknownSourceError(
            f"Unknown source_db {key!r}. Available: {', '.join(sources())}."
        )
    return reg[key]
