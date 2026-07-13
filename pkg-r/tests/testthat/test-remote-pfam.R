# Offline tests for pfam remote mode. Existence is checked against the EBI
# InterPro API, which hosts Pfam; the biobouncer.remote_transport option replaces it.

.stub_pfam <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the pfam entry endpoint", {
  source <- list(remote = list(interpro_db = "pfam"))
  url <- .remote_resolvers$interpro$url(source, "PF00001")
  expect_identical(url, "https://www.ebi.ac.uk/interpro/api/entry/pfam/PF00001")
})

test_that("an existing family is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pfam(200))
  res <- check_id("PF00001", "pfam", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "PF00001")
  expect_true(is.na(res$suggestion))
})

test_that("an absent family is invalid", {
  # The InterPro entry endpoint answers 204 for a well-formed but absent id.
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pfam(204))
  res <- check_id("PF99999", "pfam", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pfam(200))
  res <- check_id("pf00001", "pfam", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "PF00001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("PFABCDE", "pfam", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_pfam(500))
  expect_error(
    check_id("PF00001", "pfam", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("interpro", "pfam", "PF00001")))
})
