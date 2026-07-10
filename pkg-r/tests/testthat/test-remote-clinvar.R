# Offline tests for clinvar remote mode. Existence is checked against NCBI
# E-utilities esearch; the biogate.remote_transport option replaces it.

.stub_clinvar <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}
.clinvar_hits <- function(n = 1) {
  list(esearchresult = list(count = as.character(n)))
}

test_that("the url builds the esearch endpoint", {
  url <- .remote_resolvers$clinvar$url(NULL, "VCV000012345")
  expect_identical(
    url,
    paste0(
      "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
      "?db=clinvar&term=VCV000012345&retmode=json"
    )
  )
})

test_that("an existing accession is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_clinvar(200, .clinvar_hits(1))
  )
  res <- check_id("VCV000012345", "clinvar", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "VCV000012345")
  expect_true(is.na(res$suggestion))
})

test_that("an absent accession is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_clinvar(200, .clinvar_hits(0))
  )
  res <- check_id("VCV999999999", "clinvar", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_clinvar(200, .clinvar_hits(1))
  )
  res <- check_id("vcv000012345", "clinvar", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "VCV000012345")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("VCV12345", "clinvar", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_clinvar(500))
  expect_error(
    check_id("VCV000012345", "clinvar", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("clinvar", "esearch", "VCV000012345"))
  )
})
