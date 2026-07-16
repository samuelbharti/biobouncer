#!/usr/bin/env python3
"""Check that built Python artifacts carry the vendored spec and nothing else.

biobouncer is mostly data. The code in src/ is inert without the spec vendored
into src/biobouncer/_data/ by tools/sync_shared.py, so a wheel that loses that
tree still installs and imports and then fails on the first real call, for
everyone, with no way to replace the file: PyPI does not allow re-uploading a
version. The same goes the other way, where a build sweeps in whatever happens to
be sitting in the working tree. Both are cheap to check and expensive to miss.

    python tools/check_dist.py pkg-py/dist

Run it on a dist directory holding one sdist and one wheel. The release workflow
runs it between the build and the upload.
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

# Every subdirectory of _data that sync_shared.py vendors, and the count below
# which the tree is certainly truncated rather than merely trimmed. These are
# floors, not exact counts, so adding a source does not break the release.
REQUIRED_DATA = {
    "sources": 40,
    "snapshots": 10,
    "corpus": 40,
    "fixtures": 100,
    "schema": 1,
}

# Directories that exist in pkg-py/ but have no business in a source release.
# site/ is the built mkdocs output and is the one that has actually leaked.
SDIST_JUNK = ("site", "docs", "examples", "overrides", ".venv", "dist")


def fail(message: str) -> None:
    sys.exit(f"error: {message}")


def check_data(label: str, names: list[str]) -> None:
    """Confirm `names` holds a complete-looking _data tree."""
    for subdir, floor in sorted(REQUIRED_DATA.items()):
        count = sum(1 for name in names if f"_data/{subdir}/" in name)
        if count < floor:
            fail(
                f"{label}: _data/{subdir}/ has {count} files, expected at least {floor}"
            )
        print(f"  {label:5}  _data/{subdir:<10} {count} files")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.exit(f"usage: {Path(__file__).name} DIST_DIR")

    dist = Path(argv[0])
    if not dist.is_dir():
        fail(f"{dist}: not a directory")

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1:
        fail(f"{dist}: expected exactly one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        fail(f"{dist}: expected exactly one sdist, found {len(sdists)}")

    print(f"  wheel  {wheels[0].name}")
    print(f"  sdist  {sdists[0].name}")
    print()

    check_data("wheel", zipfile.ZipFile(wheels[0]).namelist())

    with tarfile.open(sdists[0]) as archive:
        sdist_names = archive.getnames()
    check_data("sdist", sdist_names)

    # Everything in an sdist sits under a single <name>-<version>/ root, so the
    # second segment is the top-level entry.
    tops = {name.split("/")[1] for name in sdist_names if len(name.split("/")) > 1}
    leaked = sorted(tops.intersection(SDIST_JUNK))
    if leaked:
        fail(f"sdist: build output leaked in: {', '.join(leaked)}")

    print()
    print("artifacts carry the vendored data and the sdist is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
