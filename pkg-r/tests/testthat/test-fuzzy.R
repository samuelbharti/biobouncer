test_that(".fuzzy_suggest picks the nearest id, ties by code point", {
  src <- .get_source("hgnc") # carries suggest$fuzzy$max_distance = 2
  ids <- c("TP53", "EGFR", "KMT2A", "KMT2D", "BRCA2")
  expect_identical(.fuzzy_suggest(src, "TP52", ids), "TP53")
  expect_identical(.fuzzy_suggest(src, "EGFF", ids), "EGFR")
  expect_true(is.na(.fuzzy_suggest(src, "ZZZZZZ", ids)))
  # KMT2E is one edit from both KMT2A and KMT2D; the code-point-smallest wins.
  expect_identical(.fuzzy_suggest(src, "KMT2E", c("KMT2A", "KMT2D")), "KMT2A")
})

test_that(".fuzzy_suggest returns NA when the source has no fuzzy config", {
  src <- .get_source("mondo") # no suggest block
  expect_true(is.na(.fuzzy_suggest(src, "MONDO:0005149", c("MONDO:0005148"))))
})
