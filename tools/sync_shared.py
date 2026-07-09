#!/usr/bin/env python3
"""Vendor the shared spec into each package.

shared/ is the single source of truth. An R build only ships files under r/ and
a Python wheel only ships files under python/, so the shared spec must be copied
into each package before build. Run this whenever shared/ changes.

The drift CI job runs this script and then fails if the committed copies differ
from a fresh sync, which catches a stale vendored copy or a hand-edit of one.

Only data files are vendored (source YAML and corpus JSONL). A package target is
skipped when its package directory does not exist yet.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"

# Shared subdirectory -> glob of files to vendor from it.
SUBDIRS = {
    "sources": "*.yaml",
    "corpus": "*.jsonl",
}

# Package directory -> vendored data root. The package directory must exist for
# its target to be written.
TARGETS = {
    "pkg-r": ROOT / "pkg-r" / "inst" / "extdata",
    "pkg-py": ROOT / "pkg-py" / "src" / "biogate" / "_data",
}


def vendor_into(dest_root: Path) -> None:
    """Mirror the shared data subdirectories into dest_root."""
    for subdir, pattern in SUBDIRS.items():
        src_dir = SHARED / subdir
        dest_dir = dest_root / subdir
        # Start clean so files removed from shared/ also disappear downstream.
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        files = sorted(src_dir.glob(pattern)) if src_dir.is_dir() else []
        if not files:
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, dest_dir / f.name)


def main() -> None:
    for pkg, dest_root in TARGETS.items():
        if (ROOT / pkg).is_dir():
            vendor_into(dest_root)


if __name__ == "__main__":
    main()
