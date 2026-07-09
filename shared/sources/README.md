# shared/sources

One declarative YAML file per source (for example `mondo.yaml`, `hgnc.yaml`).
This directory is the single source of truth for identifier patterns and source
metadata. Neither the R nor the Python package hard-codes a pattern that is not
defined here.

The schema for a source file is described in `PLAN.md`, section 5. No source
files are added yet.

Do not edit the vendored copies under `r/inst/extdata/` or
`python/src/biogate/_data/` by hand. Edit files here and run
`python tools/sync_shared.py`.
