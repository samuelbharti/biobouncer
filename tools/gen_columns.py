"""Generate the per-source synthetic column fixtures under shared/fixtures/columns/.

Each source gets a JSONL file: one row per cell of a synthetic "messy column"
(valid / repairable / invalid / missing), produced by biobouncer.synthesize and
labeled by the pattern-mode checker. Run this after changing the generator or the
source patterns, then run tools/sync_shared.py to vendor the files into both
packages. The R and Python column tests read these committed fixtures, and the
synthetic-generator tests assert that synthesize reproduces them.
"""

from __future__ import annotations

import json
from pathlib import Path

import biobouncer as bb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shared" / "fixtures" / "columns"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for source_db in bb.sources():
        rows = bb.synthesize(source_db)
        lines = []
        for row in rows:
            record = {
                "input": row["input"],
                "source_db": source_db,
                "how": "pattern",
                "category": row["category"],
                "expect": {
                    "valid": row["valid"],
                    "normalized": row["normalized"],
                    "suggestion": row["suggestion"],
                },
            }
            lines.append(json.dumps(record))
        path = OUT / f"{source_db}.cases.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        total += len(rows)
        print(f"{source_db}: {len(rows)} cells")
    print(f"\n=== {len(bb.sources())} sources, {total} cells -> {OUT} ===")


if __name__ == "__main__":
    main()
