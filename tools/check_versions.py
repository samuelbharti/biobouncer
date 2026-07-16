#!/usr/bin/env python3
"""Check that every declared version agrees.

The R and Python packages ship as one project and share a single version, so the
number is written in four places. Nothing keeps them in step on its own, and the
one that drifts is usually noticed only after a release is out, when it cannot be
taken back. This script is the check.

Run it with no argument to compare the four files to each other:

    python tools/check_versions.py

Pass a release tag to also require the files to match what is being released.
A leading "v" is optional, so both forms work:

    python tools/check_versions.py v0.1.1

The release workflow runs it with the tag before it builds anything, which is the
point where a mismatch is still free to fix.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each entry is a file and the pattern whose first group is its version. The
# patterns are anchored to the start of a line so a version named in prose or in
# a dependency pin is never picked up by mistake.
SOURCES = (
    ("pkg-py/pyproject.toml", r'^version\s*=\s*"([^"]+)"'),
    ("pkg-r/DESCRIPTION", r"^Version:\s*(\S+)"),
    ("CITATION.cff", r"^version:\s*(\S+)"),
    ("pkg-py/CHANGELOG.md", r"^##\s+(\d\S*)"),
    ("pkg-r/NEWS.md", r"^#\s+biobouncer\s+(\S+)"),
)


def read_version(relative: str, pattern: str) -> str:
    """Return the version `pattern` finds in `relative`, or exit explaining why not."""
    path = ROOT / relative
    if not path.is_file():
        sys.exit(f"{relative}: not found")
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        sys.exit(f"{relative}: no version matching {pattern!r}")
    return match.group(1).strip().strip('"')


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        sys.exit(f"usage: {Path(__file__).name} [TAG]")

    found = {name: read_version(name, pattern) for name, pattern in SOURCES}

    expected = None
    if argv:
        expected = argv[0][1:] if argv[0].startswith("v") else argv[0]

    width = max(len(name) for name in found)
    for name, version in found.items():
        print(f"  {name:<{width}}  {version}")

    distinct = set(found.values())
    if len(distinct) > 1:
        print()
        sys.exit(f"versions disagree: {', '.join(sorted(distinct))}")

    version = distinct.pop()
    if expected is not None and version != expected:
        print()
        sys.exit(f"tag is {expected} but the files say {version}")

    print()
    print(f"all versions agree: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
