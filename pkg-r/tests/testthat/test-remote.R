# Offline tests for remote mode. The biogate.remote_transport option replaces
# the network seam so no request ever leaves the machine.

.stub_present <- function(present_ids) {
  function(url, timeout) {
    id <- sub(".*obo_id=", "", url)
    if (id %in% present_ids) {
      list(status = 200, body = list(page = list(totalElements = 1)))
    } else {
      list(status = 404, body = NULL)
    }
  }
}

test_that("well-formed ids are valid when they exist remotely", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )

  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999"),
    source_db = "mondo",
    how = "remote"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$normalized, c("MONDO:0005148", NA_character_))
  expect_identical(res$suggestion, c(NA_character_, NA_character_))
  expect_true(all(nzchar(res$version)))
})

test_that("a malformed input suggests a corrected id that exists remotely", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )

  res <- check_id("mondo:5148", source_db = "mondo", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "MONDO:0005148")
})

test_that("a source with no remote block errors with a classed condition", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  expect_error(
    check_id("ENSG00000139618", source_db = "ensembl", how = "remote"),
    class = "biogate_error_no_resolver"
  )
})

test_that("an unexpected remote status raises a remote error", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      list(status = 500, body = NULL)
    }
  )
  expect_error(
    check_id("MONDO:0005148", source_db = "mondo", how = "remote"),
    class = "biogate_error_remote"
  )
})

test_that("an on-disk cached response short-circuits the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines('{"status":200,"body":{"page":{"totalElements":1}}}', path)

  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "MONDO:0005148")
})

test_that("a corrupt cached response is ignored and refetched", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines("{ this is not valid json", path)

  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
})

test_that(".remote_parse_body tolerates empty and non-json input", {
  expect_null(.remote_parse_body(""))
  expect_null(.remote_parse_body("<html>Bad Gateway</html>"))
  parsed <- .remote_parse_body('{"page":{"totalElements":2}}')
  expect_equal(parsed$page$totalElements, 2)
})

test_that(".ols_count returns 0 for missing, null, or malformed counts", {
  expect_identical(.ols_count(NULL), 0L)
  expect_identical(.ols_count(list(page = list())), 0L)
  expect_identical(.ols_count(list(page = list(totalElements = 3))), 3L)
})
