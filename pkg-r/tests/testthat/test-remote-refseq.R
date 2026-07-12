# Offline tests for refseq remote mode. Existence is checked against NCBI
# E-utilities esummary; the biobouncer.remote_transport option replaces it.

.stub_refseq <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}
.refseq_found <- function(uid = "1808862652") {
  list(result = list(uids = list(uid)))
}

test_that("the url routes by molecule prefix", {
  base <- "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
  expect_identical(
    .remote_resolvers$refseq$url(NULL, "NM_000546.6"),
    paste0(base, "?db=nuccore&id=NM_000546.6&retmode=json")
  )
  expect_identical(
    .remote_resolvers$refseq$url(NULL, "NP_003997.1"),
    paste0(base, "?db=protein&id=NP_003997.1&retmode=json")
  )
})

test_that("an existing accession is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_refseq(200, .refseq_found())
  )
  res <- check_id("NM_000546.6", "refseq", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "NM_000546.6")
  expect_true(is.na(res$suggestion))
})

test_that("an absent accession is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_refseq(
      200,
      list(result = list(uids = list()))
    )
  )
  res <- check_id("NM_999999999", "refseq", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_refseq(200, .refseq_found())
  )
  res <- check_id("nm_000546.6", "refseq", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "NM_000546.6")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("QQ_000546", "refseq", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_refseq(500))
  expect_error(
    check_id("NM_000546.6", "refseq", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("refseq", "esummary", "NM_000546.6"))
  )
})
