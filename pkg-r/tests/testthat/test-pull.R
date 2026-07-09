test_that(".parse_obo extracts the version and only matching ids", {
  lines <- c(
    "format-version: 1.2",
    "data-version: releases/2026-07-06",
    "",
    "[Term]",
    "id: MONDO:0005148",
    "name: type 2 diabetes mellitus",
    "",
    "[Term]",
    "id: MONDO:0007739",
    "",
    "[Typedef]",
    "id: RO:0002211"
  )
  parsed <- .parse_obo(lines, .get_source("mondo")$pattern)
  expect_identical(parsed$version, "2026-07-06")
  expect_identical(parsed$ids, c("MONDO:0005148", "MONDO:0007739"))
})

test_that("biogate_pull errors for a source without a builder", {
  expect_error(biogate_pull("ensembl"), class = "biogate_error_no_builder")
})
