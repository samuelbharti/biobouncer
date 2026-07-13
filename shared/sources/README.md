# shared/sources

One declarative YAML file per source (for example `mondo.yaml`, `hgnc.yaml`).
This directory is the single source of truth for identifier patterns and source
metadata. Neither the R nor the Python package hard-codes a pattern that is not
defined here.

The schema for a source file is described in `PLAN.md`, section 5, and the
"Adding a source" section of `CONTRIBUTING.md`. Each source is one YAML file in
this directory.

Do not edit the vendored copies under `pkg-r/inst/extdata/` or
`pkg-py/src/biobouncer/_data/` by hand. Edit files here and run
`python tools/sync_shared.py`.
