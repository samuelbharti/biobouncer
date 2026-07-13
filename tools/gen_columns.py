"""Generate the per-source synthetic column fixtures under shared/fixtures/columns/.

Each source gets a pattern-mode column (`<source>.cases.jsonl`); each source that
ships a snapshot also gets a cache-mode column (`<source>.cache.jsonl`). One row
per cell of a synthetic "messy column" (valid / repairable / invalid / missing),
produced by biobouncer.synthesize and labeled by the checker. Run this after
changing the generator or the source patterns, then run tools/sync_shared.py to
vendor the files into both packages. The R and Python column tests read these
committed fixtures, and the synthetic-generator tests assert that synthesize
reproduces them.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Force cache reads to the bundled snapshots so the cache columns are deterministic
# regardless of any snapshot a developer may have pulled locally. Set before the
# first check, since the cache dir is read lazily.
os.environ["BIOBOUNCER_CACHE_DIR"] = tempfile.mkdtemp()

import biobouncer as bb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shared" / "fixtures" / "columns"


def _write(
    path: Path, rows: list[dict], source_db: str, how: str, version: str | None
) -> None:
    lines = []
    for row in rows:
        record = {"input": row["input"], "source_db": source_db, "how": how}
        if version is not None:
            record["version"] = version
        record["category"] = row["category"]
        record["expect"] = {
            "valid": row["valid"],
            "normalized": row["normalized"],
            "suggestion": row["suggestion"],
        }
        lines.append(json.dumps(record))
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cache_sources = {row["key"] for row in bb.source_info() if "cache" in row["modes"]}
    total = 0
    for source_db in bb.sources():
        pattern_rows = bb.synthesize(source_db)
        _write(
            OUT / f"{source_db}.cases.jsonl", pattern_rows, source_db, "pattern", None
        )
        total += len(pattern_rows)
        if source_db in cache_sources:
            cache_rows = bb.synthesize(source_db, how="cache", version="sample")
            _write(
                OUT / f"{source_db}.cache.jsonl",
                cache_rows,
                source_db,
                "cache",
                "sample",
            )
            total += len(cache_rows)
    print(
        f"=== {len(bb.sources())} sources, {len(cache_sources)} with cache, {total} cells -> {OUT} ==="
    )


if __name__ == "__main__":
    main()
