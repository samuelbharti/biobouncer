# Offline tests for mirbase remote mode. Existence is checked against RNAcentral
# through EBI Search, which indexes miRBase; the biogate.remote_transport option
# replaces it.

.stub_mirbase <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}
.mirbase_hits <- function(n = 1) {
  list(hitCount = n)
}

test_that("the url builds the ebi search endpoint", {
  url <- .remote_resolvers$mirbase$url(NULL, "MIMAT0000001")
  expect_identical(
    url,
    paste0(
      "https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral",
      "?query=MIMAT0000001&format=json"
    )
  )
})

test_that("an existing accession is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_mirbase(200, .mirbase_hits(1))
  )
  res <- check_id("MIMAT0000001", "mirbase", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "MIMAT0000001")
  expect_true(is.na(res$suggestion))
})

test_that("an absent accession is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_mirbase(200, .mirbase_hits(0))
  )
  res <- check_id("MIMAT9999999", "mirbase", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_mirbase(200, .mirbase_hits(1))
  )
  res <- check_id("mimat0000001", "mirbase", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "MIMAT0000001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("MIMAT001", "mirbase", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_mirbase(500))
  expect_error(
    check_id("MIMAT0000001", "mirbase", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("mirbase", "rnacentral", "MIMAT0000001"))
  )
})
