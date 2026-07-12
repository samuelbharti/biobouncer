# on_error = "indeterminate": one unreachable id does not sink the batch. The
# test transport aborts with class biobouncer_error_remote to stand in for a network
# failure that has exhausted its retries.

.fail_transport <- function(url, timeout) {
  cli::cli_abort("connection refused", class = "biobouncer_error_remote")
}

.mixed_transport <- function(url, timeout) {
  if (grepl("obo_id=MONDO:0005148", url, fixed = TRUE)) {
    list(status = 200, body = list(page = list(totalElements = 1)))
  } else {
    cli::cli_abort("connection refused", class = "biobouncer_error_remote")
  }
}

test_that("the default raises on a remote failure", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .fail_transport)
  expect_error(
    check_id("MONDO:0005148", source_db = "mondo", how = "remote"),
    class = "biobouncer_error_remote"
  )
})

test_that("indeterminate isolates the failure to one id", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .mixed_transport)
  res <- check_id(
    c("MONDO:0005148", "MONDO:0000001"),
    source_db = "mondo",
    how = "remote",
    on_error = "indeterminate"
  )
  expect_true(res$valid[1])
  expect_true(is.na(res$error[1]))
  # the unreachable id is indeterminate: NA verdict with a reason, not FALSE.
  expect_true(is.na(res$valid[2]))
  expect_match(res$error[2], "connection refused")
})

test_that("a malformed input stays invalid, not indeterminate", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .fail_transport)
  res <- check_id(
    "mondo:5148",
    source_db = "mondo",
    how = "remote",
    on_error = "indeterminate"
  )
  expect_false(res$valid)
  expect_true(is.na(res$error))
})

test_that("an invalid on_error value is rejected", {
  expect_error(
    check_id("MONDO:0005148", source_db = "mondo", on_error = "nonsense"),
    class = "biobouncer_error_invalid_on_error"
  )
})
