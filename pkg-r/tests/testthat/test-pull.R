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

test_that(".parse_hgnc_tsv extracts approved symbols and a retired map", {
  tab <- "\t"
  row <- function(...) paste(c(...), collapse = tab)
  lines <- c(
    row("symbol", "status", "prev_symbol", "alias_symbol"),
    row("TP53", "Approved", "", "P53"),
    row("KMT2A", "Approved", "MLL", "MLL1|ALL-1"),
    row("KMT2D", "Approved", "MLL2|MLL4", ""),
    row("EGFR", "Entry Withdrawn", "", ""), # withdrawn, excluded
    row("CARS1", "Approved", "CARS", ""),
    row("FOO", "Approved", "SHARED", ""), # SHARED maps to two genes, dropped
    row("BAR", "Approved", "SHARED", ""),
    row("BAZ", "Approved", "TP53", ""), # TP53 is approved, never retired
    row("GENEA", "Approved", "OLD1", ""), # a previous symbol wins over an alias
    row("GENEB", "Approved", "", "OLD1")
  )
  res <- .parse_hgnc_tsv(lines, .get_source("hgnc")$pattern)
  expect_null(res$version)
  expect_identical(
    res$ids,
    c("BAR", "BAZ", "CARS1", "FOO", "GENEA", "GENEB", "KMT2A", "KMT2D", "TP53")
  )
  keys <- sort(names(res$retired), method = "radix")
  expect_identical(
    keys,
    c("ALL-1", "CARS", "MLL", "MLL1", "MLL2", "MLL4", "OLD1", "P53")
  )
  expect_identical(
    unname(res$retired[keys]),
    c("KMT2A", "CARS1", "KMT2A", "KMT2A", "KMT2D", "KMT2D", "GENEA", "TP53")
  )
})

test_that("biogate_pull errors for a source without a builder", {
  expect_error(biogate_pull("ensembl"), class = "biogate_error_no_builder")
})

test_that("biogate_pull errors for a bundled-only source", {
  # hgnc offers cache mode from a bundled snapshot but has no download builder,
  # so pull must still refuse rather than pretend it can refresh the snapshot.
  expect_error(biogate_pull("hgnc"), class = "biogate_error_no_builder")
})
