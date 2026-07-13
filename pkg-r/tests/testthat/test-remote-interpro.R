# Offline tests for interpro remote mode. Existence is checked against the EBI
# InterPro API; the biobouncer.remote_transport option replaces it.

.stub_interpro <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the interpro entry endpoint", {
  source <- list(remote = list(interpro_db = "interpro"))
  url <- .remote_resolvers$interpro$url(source, "IPR000001")
  expect_identical(
    url,
    "https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR000001"
  )
})

test_that("an existing entry is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_interpro(200))
  res <- check_id("IPR000001", "interpro", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "IPR000001")
  expect_true(is.na(res$suggestion))
})

test_that("an absent entry is invalid", {
  # The InterPro entry endpoint answers 204 for a well-formed but absent id.
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_interpro(204))
  res <- check_id("IPR999999", "interpro", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_interpro(200))
  res <- check_id("ipr000001", "interpro", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "IPR000001")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("IPRABCDEF", "interpro", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_interpro(500))
  expect_error(
    check_id("IPR000001", "interpro", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("interpro", "interpro", "IPR000001"))
  )
})
