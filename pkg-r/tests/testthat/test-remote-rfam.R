# Offline tests for rfam remote mode. Existence is checked against the Rfam API;
# the biobouncer.remote_transport option replaces it.

.stub_rfam <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the rfam family endpoint", {
  url <- .remote_resolvers$rfam$url(NULL, "RF00001")
  expect_identical(
    url,
    "https://rfam.org/family/RF00001?content-type=application/json"
  )
})

test_that("an existing family is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_rfam(200))
  res <- check_id("RF00001", "rfam", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "RF00001")
  expect_true(is.na(res$suggestion))
})

test_that("an absent family is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_rfam(404))
  res <- check_id("RF99999", "rfam", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_rfam(200))
  res <- check_id("rf00001", "rfam", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "RF00001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("RF001", "rfam", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_rfam(500))
  expect_error(
    check_id("RF00001", "rfam", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("rfam", "family", "RF00001")))
})
