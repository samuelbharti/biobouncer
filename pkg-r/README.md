# biobouncer (R package) <img src="man/figures/logo.png" align="right" height="150" alt="biobouncer logo" />

<!-- badges: start -->
[![Lifecycle: stable](https://img.shields.io/badge/lifecycle-stable-brightgreen.svg)](https://lifecycle.r-lib.org/articles/stages.html#stable)
[![CRAN status](https://www.r-pkg.org/badges/version/biobouncer)](https://CRAN.R-project.org/package=biobouncer)
[![CRAN downloads](https://cranlogs.r-pkg.org/badges/grand-total/biobouncer)](https://CRAN.R-project.org/package=biobouncer)
[![r-universe](https://samuelbharti.r-universe.dev/badges/biobouncer)](https://samuelbharti.r-universe.dev/biobouncer)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21346522-1682D4)](https://doi.org/10.5281/zenodo.21346522)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/samuelbharti/biobouncer/blob/main/LICENSE)
<!-- badges: end -->

Validate gene symbols, ontology terms, variant formats, and database
accessions from R. Checks run offline against identifier patterns and pinned
snapshots, or live against the source, and return the same verdict as the
companion Python and JavaScript packages for the same input.

All four modes work across 50 sources. `pattern` and `cache` run offline,
`remote` checks the live source, and `existence` takes the snapshot when there
is one, falls back to remote, and falls back again to pattern for a source with
no resolver.

Documentation is at <https://www.samuelbharti.com/biobouncer/r/>. The Python and
JavaScript packages are documented from
<https://www.samuelbharti.com/biobouncer/>.

## Installation

Install from CRAN:

```r
install.packages("biobouncer")

# development version from GitHub (package is in the pkg-r/ subdirectory)
pak::pak("samuelbharti/biobouncer/pkg-r")
```

R-universe also serves prebuilt binaries of the latest release:
`install.packages("biobouncer", repos = "https://samuelbharti.r-universe.dev")`.

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

## Contributing

See [`CONTRIBUTING.md`](https://github.com/samuelbharti/biobouncer/blob/main/CONTRIBUTING.md).

## License

MIT. See [`LICENSE`](https://github.com/samuelbharti/biobouncer/blob/main/LICENSE).
