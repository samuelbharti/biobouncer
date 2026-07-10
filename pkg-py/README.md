# biogate (Python package)

This directory holds the Python package for biogate. See the repository root
`README.md` for what biogate does and `PLAN.md` for the architecture.

The package is in early development. Offline `pattern` and `cache` modes, live
`remote` mode, and `existence` mode (snapshot first, then remote) work for an
initial set of sources.

## Usage

```python
import biogate

# List what can be checked.
biogate.sources()

# pattern mode: is the string well-formed?
biogate.check_id(["MONDO:0005148", "mondo:5148"], source_db="mondo")

# cache mode: does the id exist in a pinned snapshot?
biogate.check_id("MONDO:0005148", source_db="mondo", how="cache", version="sample")

# Snapshot management.
biogate.snapshots()
biogate.cache_dir()
biogate.pull("go")  # download a full snapshot into the cache directory
```

`check_id()` returns a list of `Result` records. The bundled `sample` snapshot is
a small curated subset that ships with the package for offline use.

## Development

This package uses uv. From this directory:

```sh
uv sync --dev      # create the environment and install the package
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Shared source definitions and the conformance corpus live in `shared/` at the
repository root and are vendored into `src/biogate/_data/` by
`python tools/sync_shared.py`. Do not edit the vendored copies by hand.
