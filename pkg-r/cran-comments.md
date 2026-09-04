# cran-comments

## Update

This is an update from 0.1.4 to 0.2.0. NEWS.md lists the changes. The one a
reviewer may want to notice is in `Authors@R`: two thesis advisors are added
with role `ths`, Posit Software, PBC with roles `cph` and `fnd`, and
Anthropic, PBC with role `fnd`. The LICENSE file lists both copyright
holders.

## R CMD check results

0 errors | 0 warnings | 1 note

* The CRAN incoming check flags `Hoyt` and `Dunnen` as possibly misspelled.
  They are author names in the two citations in the `Description` field.

`R CMD check --as-cran` is otherwise clean, with incoming and remote checks
enabled.

## Test environments

* Local: Windows 11, R 4.6.1
* GitHub Actions: ubuntu-latest (R-devel, R-release, R-oldrel-1),
  windows-latest (R-release), macos-latest (R-release)

## Reverse dependencies

There are no reverse dependencies on CRAN.

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
