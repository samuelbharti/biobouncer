"""Load source definitions from the vendored shared spec."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib.resources import files

import yaml


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


@functools.lru_cache(maxsize=1)
def _registry() -> dict[str, Source]:
    root = files("biogate") / "_data" / "sources"
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
        )
    return out


def sources() -> list[str]:
    """Return the sorted list of available source keys."""
    return sorted(_registry())


def get_source(key: str) -> Source:
    """Return the Source for ``key`` or raise ValueError if it is unknown."""
    reg = _registry()
    if key not in reg:
        raise ValueError(
            f"Unknown source_db {key!r}. Available: {', '.join(sources())}."
        )
    return reg[key]
