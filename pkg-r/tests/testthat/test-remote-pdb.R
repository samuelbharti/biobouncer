# Offline tests for pdb remote mode. Existence is checked against the RCSB PDB
# data API; the biobouncer.remote_transport option replaces it.

.stub_pdb <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the rcsb entry endpoint", {
  resolver <- .remote_resolvers$pdb
  url <- resolver$url(NULL, "4HHB")
  expect_identical(url, "https://data.rcsb.org/rest/v1/core/entry/4HHB")
})

test_that("an existing structure is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pdb(200))
  res <- check_id("4HHB", "pdb", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "4HHB")
  expect_true(is.na(res$suggestion))
})

test_that("an absent structure is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pdb(404))
  res <- check_id("2ZZZ", "pdb", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pdb(200))
  res <- check_id("4hhb", "pdb", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "4HHB")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("1ABCD", "pdb", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pdb(500))
  expect_error(
    check_id("4HHB", "pdb", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("pdb", "entry", "4HHB")))
})
