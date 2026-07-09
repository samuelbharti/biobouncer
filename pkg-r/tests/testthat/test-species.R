test_that(".ensembl_id_prefix extracts the species code", {
  expect_identical(.ensembl_id_prefix("ENSG00000139618"), "")
  expect_identical(.ensembl_id_prefix("ENSMUSG00000059552"), "MUS")
  expect_identical(.ensembl_id_prefix("not-an-ensembl-id"), NA_character_)
})

test_that("a human id matches the human species", {
  res <- check_id(
    "ENSG00000139618",
    source_db = "ensembl",
    species = "homo_sapiens"
  )
  expect_true(res$valid)
  expect_identical(res$normalized, "ENSG00000139618")
})

test_that("a mouse id is invalid when human is requested, with no suggestion", {
  res <- check_id(
    "ENSMUSG00000059552",
    source_db = "ensembl",
    species = "homo_sapiens"
  )
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_true(is.na(res$suggestion))
})

test_that("a taxon id matches the same species by name", {
  res <- check_id("ENSG00000139618", source_db = "ensembl", species = 9606)
  expect_true(res$valid)
  expect_identical(res$normalized, "ENSG00000139618")
})

test_that("an unknown species is not checked", {
  res <- check_id(
    "ENSG00000139618",
    source_db = "ensembl",
    species = "platypus"
  )
  expect_true(res$valid)
  expect_identical(res$normalized, "ENSG00000139618")
})

test_that("a species check applies to suggestions", {
  matched <- check_id(
    "ensmusg00000059552",
    source_db = "ensembl",
    species = "mus_musculus"
  )
  expect_false(matched$valid)
  expect_identical(matched$suggestion, "ENSMUSG00000059552")

  mismatched <- check_id(
    "ensmusg00000059552",
    source_db = "ensembl",
    species = "homo_sapiens"
  )
  expect_false(mismatched$valid)
  expect_true(is.na(mismatched$suggestion))
})

test_that("a non-species-aware source ignores species", {
  res <- check_id(
    "MONDO:0005148",
    source_db = "mondo",
    species = "homo_sapiens"
  )
  expect_true(res$valid)
  expect_identical(res$normalized, "MONDO:0005148")
})
