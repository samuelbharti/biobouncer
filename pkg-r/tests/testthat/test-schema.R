test_that("the schema version is read from the shared file", {
  expect_identical(.schema_version(), "2")
})

test_that("result fields match the check_id column order", {
  tbl <- check_id("MONDO:0005148", source_db = "mondo")
  expect_identical(names(tbl), .result_fields())
})

test_that("summarize counts each class of result", {
  tbl <- check_id(
    c("MONDO:0005148", "mondo:5148", "nope", NA),
    source_db = "mondo"
  )
  counts <- .summarize_results(tbl)
  expect_identical(names(counts), .summary_fields())
  expect_identical(counts$total, 4L)
  expect_identical(counts$valid, 1L)
  expect_identical(counts$invalid, 2L)
  expect_identical(counts$repairable, 1L)
  expect_identical(counts$missing, 1L)
  expect_identical(counts$indeterminate, 0L)
  # total is valid + invalid + missing + indeterminate; repairable subsets invalid.
  expect_identical(
    counts$total,
    counts$valid + counts$invalid + counts$missing + counts$indeterminate
  )
  expect_lte(counts$repairable, counts$invalid)
})
