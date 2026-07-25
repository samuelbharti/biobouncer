# cran-comments

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
