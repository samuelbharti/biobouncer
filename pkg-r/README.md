# biogate (R package)

This directory holds the R package for biogate. See the repository root
`README.md` for what biogate does and `PLAN.md` for the architecture.

The package is in early development. Offline `pattern` and `cache` modes work for
an initial set of sources. `remote` mode is not implemented yet.

## Usage

```r
library(biogate)

# List what can be checked.
sources()
source_info()

# pattern mode: is the string well-formed?
check_id(c("MONDO:0005148", "mondo:5148", "GO:0006915"), source_db = "mondo")

# cache mode: does the id exist in a pinned snapshot?
check_id("MONDO:0005148", source_db = "mondo", how = "cache", version = "sample")

# Snapshot management.
biogate_snapshots()
biogate_cache_dir()
biogate_pull("go") # download a full snapshot into the cache directory

# Just the verdict.
is_valid_id("P04637", source_db = "uniprot")
```

`check_id()` returns a tibble with one row per input and the columns `input`,
`valid`, `normalized`, `suggestion`, `source_db`, `version`, `species`, and
`how`.

## Development

From the repository root:

```r
# generate NAMESPACE and man pages
roxygen2::roxygenise("pkg-r")

# run the tests
testthat::test_dir("pkg-r/tests/testthat")
```

Shared source definitions and the conformance corpus live in `shared/` at the
repository root and are vendored into `inst/extdata/` by
`python tools/sync_shared.py`. Do not edit the vendored copies by hand.
