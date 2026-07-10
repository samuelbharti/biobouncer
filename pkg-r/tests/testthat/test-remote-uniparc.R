# Offline tests for uniparc remote mode. Existence is checked against the UniProt
# UniParc endpoint; the biogate.remote_transport option replaces it.

.stub_uniparc <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the uniparc endpoint", {
  url <- .remote_resolvers$uniparc$url(NULL, "UPI0000000001")
  expect_identical(url, "https://rest.uniprot.org/uniparc/UPI0000000001.json")
})

test_that("an existing sequence is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_uniparc(200))
  res <- check_id("UPI0000000001", "uniparc", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "UPI0000000001")
  expect_true(is.na(res$suggestion))
})

test_that("an absent sequence is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_uniparc(404))
  res <- check_id("UPI0000000000", "uniparc", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_uniparc(200))
  res <- check_id("upi0000000001", "uniparc", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "UPI0000000001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("UPI000000000G", "uniparc", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_uniparc(500))
  expect_error(
    check_id("UPI0000000001", "uniparc", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("uniparc", "uniparc", "UPI0000000001"))
  )
})
