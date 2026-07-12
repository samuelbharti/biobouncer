# Offline tests for reactome remote mode. Existence is checked against the
# Reactome content service; the biobouncer.remote_transport option replaces it.

.stub_reactome <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the content service query endpoint", {
  resolver <- .remote_resolvers$reactome
  url <- resolver$url(NULL, "R-HSA-68886")
  expect_identical(
    url,
    "https://reactome.org/ContentService/data/query/R-HSA-68886"
  )
})

test_that("an existing stable id is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_reactome(200))
  res <- check_id("R-HSA-68886", "reactome", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "R-HSA-68886")
  expect_true(is.na(res$suggestion))
})

test_that("an absent stable id is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_reactome(404))
  res <- check_id("R-HSA-99999999", "reactome", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_reactome(200))
  res <- check_id("r-hsa-68886", "reactome", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "R-HSA-68886")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("R-HSA-XYZ", "reactome", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_reactome(500))
  expect_error(
    check_id("R-HSA-68886", "reactome", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(file.exists(.remote_cache_path(
    "reactome",
    "query",
    "R-HSA-68886"
  )))
})
