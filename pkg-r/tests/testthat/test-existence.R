# Existence mode: answer from a snapshot when one is available for the version,
# otherwise fall back to remote. These tests set a transport that errors when it
# should not be reached, so the chosen path is unambiguous.

.forbid_network <- function(url, timeout) {
  stop("existence must use the snapshot, not the network")
}

.stub_mondo_present <- function(url, timeout) {
  id <- sub(".*obo_id=", "", url)
  if (id == "MONDO:0005148") {
    list(status = 200, body = list(page = list(totalElements = 1)))
  } else {
    list(status = 404, body = NULL)
  }
}

test_that("existence answers from a snapshot when the version is available", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .forbid_network)

  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999", "mondo:5148"),
    source_db = "mondo",
    how = "existence",
    version = "sample"
  )
  expect_identical(res$valid, c(TRUE, FALSE, FALSE))
  expect_identical(
    res$normalized,
    c("MONDO:0005148", NA_character_, NA_character_)
  )
  expect_identical(
    res$suggestion,
    c(NA_character_, NA_character_, "MONDO:0005148")
  )
  expect_identical(res$how, rep("existence", 3))
  expect_identical(res$version, rep("sample", 3))
})

test_that("existence falls back to remote when no version is given", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_mondo_present)

  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999"),
    source_db = "mondo",
    how = "existence"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$how, rep("existence", 2))
  expect_true(all(nzchar(res$version)))
  expect_false(any(res$version == "sample"))
})

test_that("existence falls back to remote when the snapshot is not installed", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_mondo_present)

  res <- check_id(
    "MONDO:0005148",
    source_db = "mondo",
    how = "existence",
    version = "2099-01-01"
  )
  expect_true(res$valid)
  # The requested snapshot is not installed, so a live timestamp is recorded.
  expect_false(identical(res$version, "2099-01-01"))
})

test_that("existence uses remote for a source that has no snapshot", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      acc <- sub(".*uniprotkb/([^.?/]+).*", "\\1", url)
      if (acc == "P01308") {
        list(
          status = 200,
          body = list(entryType = "UniProtKB reviewed (Swiss-Prot)")
        )
      } else {
        list(status = 404, body = NULL)
      }
    }
  )

  res <- check_id("P01308", source_db = "uniprot", how = "existence")
  expect_true(res$valid)
})

test_that("existence degrades to pattern for a pattern-only source", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .forbid_network)
  # cosmic is pattern-only: no snapshot and no resolver, so existence degrades to
  # a shape check instead of aborting. No network is touched.
  res <- check_id(
    c("COSM476", "nonsense"),
    source_db = "cosmic",
    how = "existence"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$how, rep("existence", 2))
  expect_true(is.na(res$version[1]))
})
