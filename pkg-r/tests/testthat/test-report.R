# report_id and repair_id: the "clean my column" entry point. The same fixed
# hgnc column as the Python test, so the two languages repair it identically.

.report_column <- c("TP53", "MLL", "ZZZZZZZZZZ", NA)
.report_repaired <- c("TP53", "KMT2A", "ZZZZZZZZZZ", NA)

test_that("report_id returns a classed table with a summary", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  rep <- report_id(.report_column, "hgnc", how = "cache")
  expect_s3_class(rep, "biogate_report")
  expect_s3_class(rep, "tbl_df")
  expect_identical(rep$input, .report_column)

  counts <- summary(rep)
  expect_identical(names(counts), c(.summary_fields()))
  expect_identical(counts$total, 4L)
  expect_identical(counts$valid, 1L)
  expect_identical(counts$invalid, 2L)
  expect_identical(counts$repairable, 1L)
  expect_identical(counts$missing, 1L)
  expect_identical(counts$indeterminate, 0L)
})

test_that("report_id prints a one-line summary above the table", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  rep <- report_id(.report_column, "hgnc", how = "cache")
  out <- paste(capture.output(print(rep)), collapse = "\n")
  expect_match(out, "biogate report on hgnc \\(cache mode\\)")
  expect_match(out, "1 valid, 1 repairable, 1 invalid, 1 missing of 4")
  # the underlying table still prints too.
  expect_match(out, "KMT2A")
})

test_that("repair_id substitutes only fixable values", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  # valid kept, retired -> successor, unmappable kept, missing kept.
  expect_identical(
    repair_id(.report_column, "hgnc", how = "cache"),
    .report_repaired
  )
})

test_that("repair_id works in pattern mode with no snapshot", {
  expect_identical(
    repair_id(c("MONDO:0005148", "mondo:5148"), "mondo"),
    c("MONDO:0005148", "MONDO:0005148")
  )
})
