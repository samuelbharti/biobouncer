test_that("check_id returns a tibble with the documented columns", {
  res <- check_id("MONDO:0005148", source_db = "mondo")
  expect_s3_class(res, "tbl_df")
  expect_identical(
    names(res),
    c(
      "input",
      "valid",
      "normalized",
      "suggestion",
      "source_db",
      "version",
      "species",
      "how"
    )
  )
})

test_that("empty input yields a zero-row result with the right columns", {
  res <- check_id(character(0), source_db = "mondo")
  expect_identical(nrow(res), 0L)
  expect_identical(ncol(res), 8L)
})

test_that("NA input yields an NA verdict and no normalized or suggestion", {
  res <- check_id(NA_character_, source_db = "mondo")
  expect_true(is.na(res$valid))
  expect_true(is.na(res$normalized))
  expect_true(is.na(res$suggestion))
})

test_that("non-character input is coerced", {
  res <- check_id(factor("MONDO:0005148"), source_db = "mondo")
  expect_true(res$valid)
})

test_that("argument validation rejects bad types", {
  expect_error(check_id(list("a"), source_db = "mondo"))
  expect_error(check_id("x", source_db = c("mondo", "efo")))
  expect_error(check_id("x", source_db = 1))
})

test_that("mode and source errors carry a condition class", {
  expect_error(
    check_id("x", source_db = "mondo", how = "bogus"),
    class = "biogate_error_invalid_mode"
  )
  expect_error(
    check_id("x", source_db = "mondo", how = "existence"),
    class = "biogate_error_unimplemented_mode"
  )
  expect_error(
    check_id("x", source_db = "not_a_source"),
    class = "biogate_error_unknown_source"
  )
})

test_that("source_info returns a tibble of metadata", {
  info <- source_info()
  expect_s3_class(info, "tbl_df")
  expect_true(all(
    c("key", "name", "species_aware", "version_aware") %in% names(info)
  ))
  expect_true("mondo" %in% info$key)
  expect_true(info$species_aware[info$key == "ensembl"])
  expect_false(info$species_aware[info$key == "mondo"])
})
