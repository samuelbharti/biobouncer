#!/usr/bin/env python3
"""Validate the shared source specs once, for all three packages.

The specs in shared/sources/ are data, and the R, Python, and JavaScript
packages read them without any check. A malformed field would surface as a
different suggestion per language, or an error in one of them, and only for the
inputs that reach it. This script fails early instead. The drift CI job runs it
next to tools/sync_shared.py, so every change to shared/ passes through one gate
whichever test suite a contributor runs locally.

    python tools/check_sources.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "shared" / "sources"


def check_one(path: Path) -> list[str]:
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if spec.get("key") != path.stem:
        problems.append(f"key {spec.get('key')!r} does not match the file name")

    pattern = spec.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        problems.append("pattern must be a non-empty string")
        return problems
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        problems.append(f"pattern does not compile: {exc}")
        return problems
    example = spec.get("example")
    if example is not None and compiled.fullmatch(str(example)) is None:
        problems.append(f"example {example!r} does not match the pattern")

    curie = spec.get("curie")
    norm = spec.get("normalize")
    if curie is not None and norm is not None:
        problems.append("curie and normalize cannot both be set; curie wins")
    if curie is not None:
        if not isinstance(curie.get("prefix"), str) or not curie["prefix"]:
            problems.append("curie.prefix must be a non-empty string")
        pad_to = curie.get("pad_to")
        if pad_to is not None and (not isinstance(pad_to, int) or pad_to < 1):
            problems.append("curie.pad_to must be a positive integer")
    if norm is not None:
        if norm.get("case") not in ("upper", "lower"):
            problems.append("normalize.case must be upper or lower")
        prefix = norm.get("keep_prefix")
        if prefix is not None and (not isinstance(prefix, str) or not prefix):
            problems.append("normalize.keep_prefix must be a non-empty string")
        unknown = set(norm) - {"case", "keep_prefix"}
        if unknown:
            problems.append(f"unknown normalize keys: {sorted(unknown)}")
    return problems


def main() -> int:
    failed = False
    for path in sorted(SOURCES.glob("*.yaml")):
        for problem in check_one(path):
            failed = True
            print(f"{path.relative_to(ROOT)}: {problem}")
    if failed:
        return 1
    print(f"  {len(list(SOURCES.glob('*.yaml')))} source specs are well formed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
