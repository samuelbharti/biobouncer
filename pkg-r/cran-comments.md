# cran-comments

## Resubmission

This is a resubmission. Thank you for the review. The three points raised are
addressed as follows.

* References are now given in the `Description` field of DESCRIPTION, in the
  requested `authors (year) <doi:...>` form with no space after `doi:`. The two
  cited works are the sources the identifier patterns follow: Hoyt et al. (2022)
  <doi:10.1038/s41597-022-01807-3> for the Bioregistry, and den Dunnen et al.
  (2016) <doi:10.1002/humu.22981> for the HGVS sequence variant nomenclature.

* The commented-out example code in `id_predicate.Rd` is removed. The examples
  for that function now run in full, and no example anywhere in the package
  contains commented-out code. The third-party integrations that were shown as
  comments (assertr, validate and pointblank) are documented in an online
  article instead, so no example depends on a package that is only suggested.

* No example requires a package from `Suggests`, so no `requireNamespace()`
  guard is needed. `Suggests` is unchanged and lists only knitr, rmarkdown,
  testthat and withr, none of which are called from an example.

## R CMD check results

0 errors | 0 warnings | 1 note

* This is a new submission.

`R CMD check --as-cran` is otherwise clean. The word "biobouncer" flagged as
possibly misspelled in the title and description is the package name.

## Test environments

* Local: Windows 11, R 4.6.1
* GitHub Actions: ubuntu-latest (R-devel, R-release, R-oldrel-1),
  windows-latest (R-release), macos-latest (R-release)

## Notes for the reviewer

* The package validates biological identifiers offline by default. The default
  test suite, examples, and the vignette do not access the network; the live
  "remote" mode is exercised only by opt-in tests gated behind the
  `BIOBOUNCER_REMOTE_TESTS` environment variable.
* Downloaded snapshots are written under `tools::R_user_dir("biobouncer",
  "cache")`, and only when the user calls `biobouncer_pull()`. Nothing is written
  to the user's home filespace or the package library.

* The one `\dontrun{}` in the package wraps the `biobouncer_pull()` example. That
  example is kept unrun rather than wrapped in `\donttest{}` because it needs a
  network connection and writes a snapshot into the user cache directory, so it
  is not safe to run during a check. Every other example runs.
