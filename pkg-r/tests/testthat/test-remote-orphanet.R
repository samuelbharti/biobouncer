# Offline tests for orphanet remote mode. Existence is checked against the ordo
# ontology in OLS, with the ORPHA prefix rewritten to Orphanet for the lookup;
# the biogate.remote_transport option replaces the network.

.stub_orphanet <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}
.orphanet_found <- function() {
  list(page = list(totalElements = 1))
}

test_that("the url rewrites the orpha prefix for ols", {
  source <- list(remote = list(ols_ontology = "ordo", obo_prefix = "Orphanet"))
  url <- .remote_resolvers$ols$url(source, "ORPHA:558")
  expect_identical(
    url,
    "https://www.ebi.ac.uk/ols4/api/ontologies/ordo/terms?obo_id=Orphanet:558"
  )
})

test_that("an existing term is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_orphanet(200, .orphanet_found())
  )
  res <- check_id("ORPHA:558", "orphanet", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "ORPHA:558")
  expect_true(is.na(res$suggestion))
})

test_that("an absent term is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_orphanet(404))
  res <- check_id("ORPHA:999999", "orphanet", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_orphanet(200, .orphanet_found())
  )
  res <- check_id("orpha:558", "orphanet", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "ORPHA:558")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("ORPHA558", "orphanet", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_orphanet(500))
  expect_error(
    check_id("ORPHA:558", "orphanet", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(file.exists(.remote_cache_path("ols", "ordo", "ORPHA:558")))
})
