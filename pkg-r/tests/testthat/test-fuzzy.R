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

test_that(".fuzzy_suggest ignores case when the source asks for it", {
  src <- .get_source("hgnc") # carries suggest$case_insensitive = TRUE
  ids <- c("TP53", "CD53", "BRCA1", "C9orf72")
  # Were case counted, tp53 would sit two edits from both TP53 and CD53 and the
  # tie-break would pick the wrong gene, and brca1 would be four edits from
  # BRCA1 and out of reach entirely.
  expect_identical(.fuzzy_suggest(src, "tp53", ids), "TP53")
  expect_identical(.fuzzy_suggest(src, "brca1", ids), "BRCA1")
  # The suggestion is the snapshot's own spelling, not an uppercased form.
  expect_identical(.fuzzy_suggest(src, "C9ORF72", ids), "C9orf72")
  # Case is free, but a real edit still costs, so a lowercase typo resolves to
  # TP53 rather than to the two-edit CD52.
  expect_identical(.fuzzy_suggest(src, "tp52", c("TP53", "CD52")), "TP53")
  expect_true(is.na(.fuzzy_suggest(src, "zzzzzz", ids)))
  # Ties still break on the original spelling by code point.
  expect_identical(.fuzzy_suggest(src, "kmt2e", c("KMT2A", "KMT2D")), "KMT2A")
})

test_that(".fuzzy_suggest counts case when the source does not opt in", {
  # The flag drives this, not the code: with it off, case costs an edit again.
  src <- .get_source("hgnc")
  src$suggest$case_insensitive <- NULL
  expect_identical(.fuzzy_suggest(src, "tp53", c("TP53", "CD53")), "CD53")
  expect_true(is.na(.fuzzy_suggest(src, "brca1", c("BRCA1"))))
})
