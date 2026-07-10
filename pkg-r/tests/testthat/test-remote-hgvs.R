# Offline tests for hgvs remote mode. Existence is checked against the Mutalyzer
# normalizer; the biogate.remote_transport option replaces the network.

.stub_mutalyzer_status <- function(status) {
  function(url, timeout) list(status = status, body = NULL)
}

test_that("safe_ident replaces filename-unsafe characters", {
  expect_identical(
    .safe_ident("NM_004006.2:c.4375C>T"),
    "NM_004006.2_c.4375C_T"
  )
  expect_identical(.safe_ident("A/B C"), "A_B_C")
  expect_identical(.safe_ident("NM_004006.2"), "NM_004006.2")
})

test_that("the remote cache path for a variant has no unsafe characters", {
  path <- .remote_cache_path("mutalyzer", "normalize", "NM_004006.2:c.4375C>T")
  base <- basename(path)
  expect_false(grepl("[>:]", base))
  expect_identical(base, "NM_004006.2_c.4375C_T.json")
})

test_that("a valid variant is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_mutalyzer_status(200))
  res <- check_id("NM_004006.2:c.4375C>T", "hgvs", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "NM_004006.2:c.4375C>T")
  expect_true(is.na(res$suggestion))
})

test_that("a reference-inconsistent variant is invalid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_mutalyzer_status(422))
  res <- check_id("NM_004006.2:c.4375A>T", "hgvs", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_true(is.na(res$suggestion))
})

test_that("a malformed variant skips the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("a malformed variant must not reach the network")
    }
  )
  res <- check_id("NM_004006.2:c.76insG", "hgvs", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_mutalyzer_status(500))
  expect_error(
    check_id("NM_004006.2:c.4375C>T", "hgvs", how = "remote"),
    class = "biogate_error_remote"
  )
  expect_false(file.exists(
    .remote_cache_path("mutalyzer", "normalize", "NM_004006.2:c.4375C>T")
  ))
})

test_that("the disk cache short-circuits the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_mutalyzer_status(200))
  expect_true(check_id("NM_004006.2:c.4375C>T", "hgvs", how = "remote")$valid)
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network should not be called on a cache hit")
    }
  )
  expect_true(check_id("NM_004006.2:c.4375C>T", "hgvs", how = "remote")$valid)
})
