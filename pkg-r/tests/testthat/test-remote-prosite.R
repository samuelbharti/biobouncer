# Offline tests for prosite remote mode. Existence is checked against the ExPASy
# PROSITE entry endpoint, which resolves patterns and profiles alike; the
# biogate.remote_transport option replaces it.

.stub_prosite <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the expasy entry endpoint", {
  url <- .remote_resolvers$prosite$url(NULL, "PS00001")
  expect_identical(url, "https://prosite.expasy.org/PS00001")
})

test_that("an existing pattern is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_prosite(200))
  res <- check_id("PS00001", "prosite", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "PS00001")
  expect_true(is.na(res$suggestion))
})

test_that("an existing profile is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_prosite(200))
  res <- check_id("PS50011", "prosite", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "PS50011")
})

test_that("an absent entry is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_prosite(404))
  res <- check_id("PS99999", "prosite", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_prosite(200))
  res <- check_id("ps00001", "prosite", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "PS00001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("PS001", "prosite", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_prosite(500))
  expect_error(
    check_id("PS00001", "prosite", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("prosite", "entry", "PS00001")))
})
