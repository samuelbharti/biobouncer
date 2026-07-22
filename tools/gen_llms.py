#!/usr/bin/env python3
"""Generate the llms.txt index and the llms-full.txt full-context file.

An agent asked to validate or clean a column of identifiers has no single file
that describes biobouncer. The docs are spread across a pkgdown site, a MkDocs
site, and several READMEs. The llms.txt convention (https://llmstxt.org) closes
that gap: a short curated index, and a full file an agent can paste as context.

llms-full.txt is the Python documentation pages concatenated behind a generated
header, so it is regenerated from the docs rather than hand-written. A
hand-written copy would drift the first time a page or the API changed. Run

    python tools/gen_llms.py

to rewrite both files, and

    python tools/gen_llms.py --check

to fail if the committed files are stale, which the docs workflow runs on every
pull request. Both files are Python-led with a compact R map, because the two
packages return the same verdict for the same input by construction and the R
prose would only repeat what the Python pages already say.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "pkg-py" / "docs"
OUT_DIR = ROOT / "docs-hub"

SITE = "https://www.samuelbharti.com/biobouncer"
REPO = "https://github.com/samuelbharti/biobouncer"
PYPI = "https://pypi.org/project/biobouncer"
RUNIVERSE = "https://samuelbharti.r-universe.dev"

# The prose pages, in reading order. reference.md is skipped: it is only
# mkdocstrings ::: directives, not prose an agent can read.
PAGES = ["index.md", "guide.md", "report.md", "examples.md", "cli.md", "sources.md"]


def package_version() -> str:
    """The version in pyproject.toml, read the way check_versions.py reads it."""
    text = (ROOT / "pkg-py" / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        sys.exit("could not read the version from pkg-py/pyproject.toml")
    return match.group(1)


def source_count() -> int:
    """The number of sources, counted from the canonical specs, never hard-coded."""
    return len(list((ROOT / "shared" / "sources").glob("*.yaml")))


def page_url(name: str) -> str:
    """The deployed URL of a docs page. MkDocs serves directory URLs by default."""
    stem = Path(name).stem
    return f"{SITE}/py/" if stem == "index" else f"{SITE}/py/{stem}/"


def rewrite_links(text: str) -> str:
    """Turn relative MkDocs links into the absolute URLs they deploy to.

    A link like `(guide.md#modes)` only resolves inside the MkDocs site, so in
    the concatenated file it is rewritten to the hosted page and anchor. Links
    inside fenced code blocks are left alone.
    """
    out, in_fence = [], False
    link = re.compile(r"\]\((?!https?://)([a-z_]+)\.md(#[^)]*)?\)")

    def replace(match: re.Match) -> str:
        anchor = match.group(2) or ""
        return f"]({page_url(match.group(1) + '.md')}{anchor})"

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(line)
        else:
            out.append(link.sub(replace, line))
    return "\n".join(out)


def header(version: str, sources: int) -> str:
    """The generated preamble of llms-full.txt: what biobouncer is and how to call it."""
    return f"""# biobouncer

> A gate for biological inputs. It validates gene symbols, ontology terms,
> variant formats, and database identifiers, and returns the same verdict in
> Python and R.

Version {version}. {sources} sources.

biobouncer answers one question, "is this a valid identifier?", for a value or a
whole column. It is offline by default and has no required heavy dependencies.
The Python and R packages return the same verdict for the same input, enforced by
a shared conformance corpus, so the API below applies to both.

## Install

```bash
# Python
pip install biobouncer
```

```r
# R (not on CRAN yet)
install.packages("biobouncer", repos = "{RUNIVERSE}")
```

## The four modes

`check_id(..., how=)` selects how strict and how online the check is.

| mode | question | network |
|------|----------|---------|
| `pattern` | is the string well-formed? (default) | offline |
| `cache` | does the id exist in a pinned local snapshot? | offline |
| `remote` | does the id exist right now in the source? | live |
| `existence` | snapshot if present, else remote, else pattern | live |

Cache mode uses the newest snapshot already installed for the source, so no
`version` argument is needed. `hgnc` and several ontologies ship one, so
`how="cache"` works offline out of the box. `pull()` downloads a fresh snapshot
for a source that has no bundled one, or to update an existing one.

## The result

Every check returns one record per input, in order, with these fields:
`input`, `valid`, `normalized`, `suggestion`, `source_db`, `version`, `species`,
`how`, `error`. A missing input keeps `valid` empty rather than turning into a
silent `False`. `suggestion` holds the repaired form of a wrong but fixable id.

## Python and R

The core API is identical. A few names carry a package prefix in R:

| Python | R |
|--------|---|
| `check_id`, `is_valid_id` | `check_id`, `is_valid_id` |
| `sources`, `source_info` | `sources`, `source_info` |
| `report`, `Report.repair` | `report_id`, `repair_id` |
| `pull` | `biobouncer_pull` |
| `snapshots` | `biobouncer_snapshots` |
| `cache_dir` | `biobouncer_cache_dir` |

The pages below are the Python documentation. Read a Python function name through
the table above to get its R equivalent; the arguments and the verdict are the
same.
"""


def agent_section() -> str:
    """The closing section, so the full file also explains how an agent should use it."""
    return f"""## Using biobouncer from an AI agent

Point your agent at this file so it knows the API, then ask it to validate or
clean a data file. The agent can install biobouncer with the commands above.

Example prompt:

> Read {SITE}/llms-full.txt. Then use biobouncer in Python to validate and repair
> the `gene` column of `data.csv` against `hgnc` in cache mode, write the cleaned
> table to `data_clean.csv`, and preserve the row order.

The everyday job is one call. `report(column, source_db, how="cache")` returns a
report whose `.repair()` substitutes the fixable values and leaves valid, missing,
and unmappable ones untouched, preserving order and length. In R the same call is
`repair_id(column, source_db, how = "cache")`.
"""


def build_full(version: str, sources: int) -> str:
    """The whole llms-full.txt: header, every prose page, then the agent section."""
    parts = [header(version, sources).rstrip()]
    for name in PAGES:
        body = rewrite_links((DOCS / name).read_text(encoding="utf-8").rstrip())
        parts.append(
            f"<!-- source: pkg-py/docs/{name} ({page_url(name)}) -->\n\n{body}"
        )
    parts.append(agent_section().rstrip())
    return "\n\n---\n\n".join(parts) + "\n"


def build_index(version: str, sources: int) -> str:
    """The curated llms.txt index: a summary and links, no full content."""
    return f"""# biobouncer

> A gate for biological inputs. It validates gene symbols, ontology terms,
> variant formats, and database identifiers across {sources} sources, and returns
> the same verdict in Python and R. Version {version}.

## Documentation

- [Full context for LLMs]({SITE}/llms-full.txt): the whole API and usage in one file.
- [Overview]({SITE}/): what biobouncer is, with install and a first example.
- [Python documentation]({SITE}/py/): guide, column cleaning, examples, CLI, and API reference.
- [R documentation]({SITE}/r/): reference and vignettes.

## Use it

- [Install for Python]({PYPI}/): `pip install biobouncer`.
- [Install for R]({RUNIVERSE}): `install.packages("biobouncer", repos = "{RUNIVERSE}")`.
- [Demo notebooks]({REPO}/tree/main/demo): the same story in Python and R over messy data.

## Source

- [Repository]({REPO}): source code, issues, and the shared cross-language spec.
"""


def write(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def check(path: Path, content: str) -> bool:
    """True if `path` already holds `content` (line endings normalized)."""
    if not path.is_file():
        print(f"  missing: {path.relative_to(ROOT)}")
        return False
    current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if current == content:
        return True
    print(f"  stale:   {path.relative_to(ROOT)}")
    return False


def main(argv: list[str]) -> int:
    checking = argv == ["--check"]
    if argv and not checking:
        sys.exit(f"usage: {Path(__file__).name} [--check]")

    version, sources = package_version(), source_count()
    files = {
        OUT_DIR / "llms.txt": build_index(version, sources),
        OUT_DIR / "llms-full.txt": build_full(version, sources),
    }

    if checking:
        if all(check(path, content) for path, content in files.items()):
            print("  llms.txt and llms-full.txt are current")
            return 0
        sys.exit("run `python tools/gen_llms.py` and commit the result")

    for path, content in files.items():
        write(path, content)
        print(f"  wrote {path.relative_to(ROOT)} ({len(content.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
