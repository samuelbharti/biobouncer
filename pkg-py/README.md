# biogate (Python package)

This directory holds the Python package for biogate. See the repository root
`README.md` for what biogate does and `PLAN.md` for the architecture.

The package is an early scaffold. It installs and passes checks but has no public
functions yet.

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
