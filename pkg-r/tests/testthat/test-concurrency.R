# Bounded concurrency for remote checks. The concurrent fetch runs on the live
# path only (curl::multi_run); with a test transport set it stays sequential, so
# these offline tests exercise the guard, not the network.

test_that(".remote_workers reads BIOGATE_REMOTE_WORKERS", {
  withr::local_envvar(BIOGATE_REMOTE_WORKERS = "")
  expect_identical(.remote_workers(), 1L)
  withr::local_envvar(BIOGATE_REMOTE_WORKERS = "8")
  expect_identical(.remote_workers(), 8L)
  withr::local_envvar(BIOGATE_REMOTE_WORKERS = "0")
  expect_identical(.remote_workers(), 1L)
  withr::local_envvar(BIOGATE_REMOTE_WORKERS = "junk")
  expect_identical(.remote_workers(), 1L)
})

test_that("a set transport keeps resolution sequential even with workers set", {
  withr::local_envvar(
    BIOGATE_CACHE_DIR = withr::local_tempdir(),
    BIOGATE_REMOTE_WORKERS = "4"
  )
  # The test transport is synchronous, so concurrency must be skipped; the
  # verdicts must still be correct and deterministic.
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      if (grepl("obo_id=MONDO:0005148", url, fixed = TRUE)) {
        list(status = 200, body = list(page = list(totalElements = 1)))
      } else {
        list(status = 404, body = NULL)
      }
    }
  )
  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999"),
    source_db = "mondo",
    how = "remote"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
})
