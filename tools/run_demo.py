#!/usr/bin/env python3
"""Run the demo notebooks against the working tree.

A demo that is not executed rots, and a rotted demo misrepresents the package to
exactly the people deciding whether to use it. This runs the notebooks in CI so a
change that breaks them fails the pull request instead of being found later.

    python tools/run_demo.py python     # execute the Python notebook
    python tools/run_demo.py r          # run the R notebook's code through Rscript
    python tools/run_demo.py python --save   # execute and write outputs back

The notebook names the stock "python3" kernel so it opens anywhere. Pass
--kernel NAME to run it against a different environment, which is how the
checkout under test gets used instead of whatever "python3" happens to point at.

The cell tagged "install" is skipped in both notebooks. It installs biobouncer
from PyPI or R-universe for a reader, but CI needs the checkout under test, not
the last release, or a break would not surface until after it shipped.

The remote-mode cells reach the network. Both notebooks already guard them, with
try/except in Python and tryCatch in R, so this runs offline as well.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"

PYTHON_NB = DEMO / "biobouncer_python.ipynb"
R_NB = DEMO / "biobouncer_r.ipynb"


def code_cells(path: Path) -> list[str]:
    """Every code cell in `path` except the install cell, as source strings."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        if "install" in cell.get("metadata", {}).get("tags", []):
            continue
        out.append("".join(cell["source"]))
    return out


def run_python(save: bool, kernel: str) -> int:
    """Execute the Python notebook and report the first cell that fails."""
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError:
        sys.exit("nbclient and nbformat are required: uv pip install nbclient nbformat")

    nb = nbformat.read(PYTHON_NB, as_version=4)
    # Drop the install cell rather than skipping it at execution time, so its
    # stale outputs cannot survive into a saved notebook.
    kept = [
        c
        for c in nb.cells
        if not (
            c.cell_type == "code" and "install" in c.get("metadata", {}).get("tags", [])
        )
    ]
    removed = len(nb.cells) - len(kept)
    nb.cells = kept
    print(
        f"  executing {PYTHON_NB.name} ({len(kept)} cells, {removed} install skipped)"
    )

    client = NotebookClient(
        nb,
        timeout=300,
        kernel_name=kernel,
        resources={"metadata": {"path": str(DEMO)}},
        allow_errors=False,
    )
    client.execute()
    print("  Python notebook ran clean")

    if save:
        original = nbformat.read(PYTHON_NB, as_version=4)
        executed = iter(nb.cells)
        for i, cell in enumerate(original.cells):
            if cell.cell_type == "code" and "install" in cell.get("metadata", {}).get(
                "tags", []
            ):
                cell["outputs"] = []
                cell["execution_count"] = None
                continue
            done = next(executed)
            original.cells[i] = done
        nbformat.write(original, PYTHON_NB)
        print(f"  wrote outputs back to {PYTHON_NB.name}")
    return 0


def run_r() -> int:
    """Run the R notebook's code cells through Rscript.

    Rscript rather than a Jupyter R kernel: it needs no IRkernel and no kernel
    registration in CI, and it still fails on any error in the demo's code.
    """
    cells = code_cells(R_NB)
    script = "\n\n".join(cells)
    print(f"  running {R_NB.name} ({len(cells)} cells) through Rscript")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".R", delete=False, encoding="utf-8", newline="\n"
    ) as handle:
        # A cell ending in a bare expression prints under Jupyter but not under
        # Rscript, so this checks that the demo runs, not what it displays.
        # Warnings surface immediately so a failure points at the right cell.
        handle.write("options(warn = 1)\n")
        handle.write(script)
        path = handle.name

    try:
        proc = subprocess.run(
            ["Rscript", "--vanilla", path], cwd=DEMO, text=True, capture_output=True
        )
    finally:
        Path(path).unlink(missing_ok=True)

    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        print(proc.stderr.rstrip(), file=sys.stderr)
        sys.exit(f"R demo failed with exit code {proc.returncode}")
    print("  R notebook ran clean")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"python", "r"}:
        sys.exit(f"usage: {Path(__file__).name} (python|r) [--save] [--kernel NAME]")
    if argv[0] == "python":
        kernel = "python3"
        if "--kernel" in argv:
            kernel = argv[argv.index("--kernel") + 1]
        return run_python(save="--save" in argv, kernel=kernel)
    return run_r()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
