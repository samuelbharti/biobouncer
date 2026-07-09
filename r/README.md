# biogate (R package)

This directory holds the R package for biogate. See the repository root
`README.md` for what biogate does and `PLAN.md` for the architecture.

The package is an early scaffold. It installs and passes checks but has no public
functions yet.

## Development

From the repository root:

```r
# generate NAMESPACE and man pages
roxygen2::roxygenise("r")

# run the tests
testthat::test_dir("r/tests/testthat")
```

Shared source definitions and the conformance corpus live in `shared/` at the
repository root and are vendored into `inst/extdata/` by
`python tools/sync_shared.py`. Do not edit the vendored copies by hand.
