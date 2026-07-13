# Adapters wrap is_valid_id for other validation frameworks.

test_that("check_valid_id returns TRUE for all-valid, else a message", {
  expect_true(check_valid_id(c("MONDO:0005148", "MONDO:0018076"), "mondo"))
  msg <- check_valid_id(c("MONDO:0005148", "mondo:5148"), "mondo")
  expect_type(msg, "character")
  expect_match(msg, "mondo")
})

test_that("assert_valid_id errors on invalid and returns x on valid", {
  expect_error(assert_valid_id("mondo:5148", "mondo"))
  expect_identical(assert_valid_id("MONDO:0005148", "mondo"), "MONDO:0005148")
})

test_that("test_valid_id returns a single logical", {
  expect_true(test_valid_id(c("MONDO:0005148", "MONDO:0018076"), "mondo"))
  expect_false(test_valid_id("mondo:5148", "mondo"))
})

test_that("sv_biobouncer produces a shinyvalidate-style rule", {
  rule <- sv_biobouncer("mondo")
  expect_null(rule("MONDO:0005148"))
  expect_type(rule("mondo:5148"), "character")
  custom <- sv_biobouncer("mondo", message = "bad id")
  expect_identical(custom("mondo:5148"), "bad id")
})

test_that("a missing cell is not a failure across the adapters", {
  # NA is missing, not a failed id, matching the pandera and narwhals column
  # checks in the Python package.
  expect_true(check_valid_id(c("MONDO:0005148", NA), "mondo"))
  expect_identical(
    assert_valid_id(c("MONDO:0005148", NA), "mondo"),
    c("MONDO:0005148", NA)
  )
  expect_true(test_valid_id(c("MONDO:0005148", NA), "mondo"))
  expect_null(sv_biobouncer("mondo")(NA))
  is_mondo <- id_predicate("mondo")
  expect_identical(
    is_mondo(c("MONDO:0005148", NA, "mondo:5148")),
    c(TRUE, TRUE, FALSE)
  )
  # a missing cell survives a filter rather than being dropped or NA-indexed.
  ids <- c("MONDO:0005148", NA, "mondo:5148")
  expect_identical(ids[is_mondo(ids)], c("MONDO:0005148", NA))
})

test_that("check_valid_id still flags a real failure alongside a missing cell", {
  msg <- check_valid_id(c("MONDO:0005148", NA, "mondo:5148"), "mondo")
  expect_type(msg, "character")
  expect_match(msg, "1 of 3 failed")
})

test_that("adapters thread how and version to the core", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  expect_true(
    test_valid_id("MONDO:0005148", "mondo", how = "cache", version = "sample")
  )
  expect_false(
    test_valid_id("MONDO:9999999", "mondo", how = "cache", version = "sample")
  )
})

test_that("id_predicate returns an elementwise logical vector", {
  is_mondo <- id_predicate("mondo")
  ids <- c("MONDO:0005148", "mondo:5148", "MONDO:0018076")
  expect_identical(is_mondo(ids), c(TRUE, FALSE, TRUE))
  expect_identical(ids[is_mondo(ids)], c("MONDO:0005148", "MONDO:0018076"))
})

test_that("id_predicate threads how and version to the core", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  is_sample <- id_predicate("mondo", how = "cache", version = "sample")
  expect_identical(
    is_sample(c("MONDO:0005148", "MONDO:9999999")),
    c(TRUE, FALSE)
  )
})
