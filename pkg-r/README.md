# biobouncer (R package)

This directory holds the R package for biobouncer. See the repository root
`README.md` for what biobouncer does and `PLAN.md` for the architecture.

The package is in early development. Offline `pattern` and `cache` modes, live
`remote` mode, and `existence` mode (snapshot first, then remote) work for an
initial set of sources.

## Usage

```r
library(biobouncer)

# List what can be checked.
sources()
source_info()

# pattern mode: is the string well-formed?
check_id(c("MONDO:0005148", "mondo:5148", "GO:0006915"), source_db = "mondo")

# cache mode: does the id exist in a pinned snapshot?
check_id("MONDO:0005148", source_db = "mondo", how = "cache", version = "sample")

# Snapshot management.
biobouncer_snapshots()
biobouncer_cache_dir()
biobouncer_pull("go") # download a full snapshot into the cache directory

# Just the verdict.
is_valid_id("P04637", source_db = "uniprot")
```

`check_id()` returns a tibble with one row per input and the columns `input`,
`valid`, `normalized`, `suggestion`, `source_db`, `version`, `species`, `how`,
and `error` (the reason a remote check was left indeterminate, else `NA`).

## Validation frameworks

Adapters wrap the core classifier so it plugs into common validation
frameworks. They never reimplement any checks.

```r
# checkmate style: check, assert, or test.
check_valid_id(c("MONDO:0005148", "mondo:5148"), "mondo")
assert_valid_id("MONDO:0005148", "mondo")
test_valid_id("MONDO:0005148", "mondo")

# shinyvalidate rule.
iv <- shinyvalidate::InputValidator$new()
iv$add_rule("term", sv_biobouncer("mondo"))

# Data-frame validation. id_predicate() returns an elementwise predicate.
is_mondo <- id_predicate("mondo")

# assertr:
df |> assertr::assert(is_mondo, term)

# validate:
rules <- validate::validator(good_terms = is_mondo(term))
validate::confront(df, rules)
```

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
