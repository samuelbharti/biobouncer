# Offline tests for dbsnp remote mode. Existence and merge handling are checked
# against the NCBI RefSNP API; the biogate.remote_transport option replaces it.

.merged_body <- list(merged_snapshot_data = list(merged_into = list("7412")))

.stub_dbsnp <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url strips the rs prefix", {
  resolver <- .remote_resolvers$dbsnp
  url <- resolver$url(NULL, "rs7412")
  expect_true(endsWith(url, "/refsnp/7412"))
})

test_that("a current rsID is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_dbsnp(200))
  res <- check_id("rs7412", "dbsnp", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "rs7412")
  expect_true(is.na(res$suggestion))
})

test_that("a merged rsID is invalid and suggests the primary id", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_dbsnp(200, .merged_body)
  )
  res <- check_id("rs3200542", "dbsnp", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "rs7412")
})

test_that("an absent rsID is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_dbsnp(404))
  res <- check_id("rs999999999999", "dbsnp", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("ss12345", "dbsnp", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_dbsnp(500))
  expect_error(
    check_id("rs7412", "dbsnp", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("dbsnp", "refsnp", "rs7412")))
})

test_that("a merge round-trips through the cache", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_dbsnp(200, .merged_body)
  )
  expect_identical(
    check_id("rs3200542", "dbsnp", how = "remote")$suggestion,
    "rs7412"
  )
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network should not be called on a cache hit")
    }
  )
  expect_identical(
    check_id("rs3200542", "dbsnp", how = "remote")$suggestion,
    "rs7412"
  )
})
