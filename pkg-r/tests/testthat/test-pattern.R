test_that("sources() lists keys, sorted", {
  keys <- sources()
  expect_true("mondo" %in% keys)
  expect_identical(keys, sort(keys))
})

test_that("check_id returns one row per input and preserves order", {
  xs <- c("MONDO:0005148", "nonsense", "mondo:5148")
  res <- check_id(xs, source_db = "mondo")
  expect_identical(res$input, xs)
  expect_identical(res$valid, c(TRUE, FALSE, FALSE))
  expect_identical(res$normalized[1], "MONDO:0005148")
  expect_identical(res$suggestion[3], "MONDO:0005148")
  expect_identical(nrow(res), 3L)
})

test_that("is_valid_id returns a logical vector", {
  expect_identical(
    is_valid_id(c("MONDO:0005148", "x"), source_db = "mondo"),
    c(TRUE, FALSE)
  )
})

test_that("species is echoed and version is NA in pattern mode", {
  res <- check_id(
    "ENSG00000139618",
    source_db = "ensembl",
    species = "homo_sapiens"
  )
  expect_identical(res$species, "homo_sapiens")
  expect_true(is.na(res$version))
})

test_that("a numeric species (taxon id) is echoed as a string", {
  res <- check_id("ENSG00000139618", source_db = "ensembl", species = 9606)
  expect_identical(res$species, "9606")
})
