# Offline tests for chembl remote mode. Existence is checked against the ChEMBL
# id-lookup endpoint; the biobouncer.remote_transport option replaces it.

.stub_chembl <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the chembl id-lookup endpoint", {
  resolver <- .remote_resolvers$chembl
  url <- resolver$url(NULL, "CHEMBL25")
  expect_identical(
    url,
    "https://www.ebi.ac.uk/chembl/api/data/chembl_id_lookup/CHEMBL25.json"
  )
})

test_that("an existing entity is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_chembl(200))
  res <- check_id("CHEMBL25", "chembl", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "CHEMBL25")
  expect_true(is.na(res$suggestion))
})

test_that("an absent entity is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_chembl(404))
  res <- check_id("CHEMBL99999999", "chembl", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_chembl(200))
  res <- check_id("chembl25", "chembl", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "CHEMBL25")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("CHEMBLABC", "chembl", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_chembl(500))
  expect_error(
    check_id("CHEMBL25", "chembl", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("chembl", "lookup", "CHEMBL25")))
})
