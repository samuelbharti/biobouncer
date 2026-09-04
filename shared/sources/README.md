# shared/sources

One declarative YAML file per source (for example `mondo.yaml`, `hgnc.yaml`).
This directory is the single source of truth for identifier patterns and source
metadata. None of the R, Python, or JavaScript packages hard-codes a pattern
that is not defined here.

The schema for a source file is described in the "Adding a source" section of
`CONTRIBUTING.md`. Each source is one YAML file in this directory.

Do not edit the vendored copies under `pkg-r/inst/extdata/`,
`pkg-py/src/biobouncer/_data/`, or `pkg-js/src/_data/` by hand. Edit files
here and run `python tools/sync_shared.py`.
