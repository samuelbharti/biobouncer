#!/usr/bin/env python3
"""Vendor the shared spec into each package.

shared/ is the single source of truth. An R build only ships files under pkg-r/
and a Python wheel only ships files under pkg-py/, so the shared spec must be
copied into each package before build. Run this whenever shared/ changes.

The drift CI job runs this script and then fails if the committed copies differ
from a fresh sync, which catches a stale vendored copy or a hand-edit of one.

The whole shared/ tree is mirrored (sources, corpus, snapshots), excluding
documentation and placeholders. A package target is skipped when its package
directory does not exist yet.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"

# Files that document the spec but are not part of it.
SKIP_NAMES = {"README.md", ".gitkeep"}

# Package directory -> vendored data root. The package directory must exist for
# its target to be written.
TARGETS = {
    "pkg-r": ROOT / "pkg-r" / "inst" / "extdata",
    "pkg-py": ROOT / "pkg-py" / "src" / "biobouncer" / "_data",
}


def _shared_files() -> list[Path]:
    return sorted(
        p for p in SHARED.rglob("*") if p.is_file() and p.name not in SKIP_NAMES
    )


def vendor_into(dest_root: Path) -> None:
    """Mirror the shared tree into dest_root.

    Stale files are removed and current files are overwritten in place. A
    destination directory is never removed, which avoids a Windows file lock
    (for example from a synced folder) failing the whole sync.
    """
    wanted = {p.relative_to(SHARED) for p in _shared_files()}
    if dest_root.exists():
        for existing in dest_root.rglob("*"):
            if existing.is_file() and existing.relative_to(dest_root) not in wanted:
                existing.unlink()
    for rel in sorted(wanted):
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SHARED / rel, dest)


def main() -> None:
    for pkg, dest_root in TARGETS.items():
        if (ROOT / pkg).is_dir():
            vendor_into(dest_root)


if __name__ == "__main__":
    main()
