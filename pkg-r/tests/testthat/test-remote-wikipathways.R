# Offline tests for wikipathways remote mode. Existence is checked against the
# published WikiPathways asset; the biogate.remote_transport option replaces it.

.stub_wikipathways <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the asset endpoint", {
  url <- .remote_resolvers$wikipathways$url(NULL, "WP554")
  expect_identical(
    url,
    "https://www.wikipathways.org/wikipathways-assets/pathways/WP554/WP554.gpml"
  )
})

test_that("an existing pathway is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_wikipathways(200))
  res <- check_id("WP554", "wikipathways", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "WP554")
  expect_true(is.na(res$suggestion))
})

test_that("an absent pathway is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_wikipathways(404))
  res <- check_id("WP9999999", "wikipathways", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_wikipathways(200))
  res <- check_id("wp554", "wikipathways", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "WP554")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("WPXYZ", "wikipathways", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_wikipathways(500))
  expect_error(
    check_id("WP554", "wikipathways", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("wikipathways", "pathways", "WP554"))
  )
})
