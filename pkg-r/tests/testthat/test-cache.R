test_that("cache mode checks existence against the bundled sample", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999", "mondo:5148"),
    source_db = "mondo",
    how = "cache",
    version = "sample"
  )
  expect_identical(res$valid, c(TRUE, FALSE, FALSE))
  expect_identical(res$normalized[1], "MONDO:0005148")
  expect_identical(res$suggestion[3], "MONDO:0005148")
  expect_identical(res$how, rep("cache", 3))
  expect_identical(res$version, rep("sample", 3))
})

test_that("a well-formed but absent suggestion is not offered in cache mode", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  # mondo:9999999 suggests MONDO:9999999, which is not in the sample snapshot.
  res <- check_id(
    "mondo:9999999",
    source_db = "mondo",
    how = "cache",
    version = "sample"
  )
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("cache mode defaults to the latest installed snapshot", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  # With no version, cache mode uses the latest installed snapshot instead of
  # forcing a magic version = "sample". The bundled sample is the only one here.
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "cache")
  expect_true(res$valid)
  expect_identical(res$version, "sample")
})

test_that("cache default prefers the source's pinned default_version", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  # hgnc pins default_version; the default resolves to it, not the sample.
  res <- check_id("TP53", source_db = "hgnc", how = "cache")
  expect_true(res$valid)
  expect_identical(res$version, "2026-07-07")
})

test_that("a defaulted cache check resolves to a newly bundled snapshot", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  # doid now ships a bundled sample snapshot, so a defaulted cache check
  # resolves to it instead of erroring.
  res <- check_id("DOID:9352", source_db = "doid", how = "cache")
  expect_true(res$valid)
  expect_identical(res$version, "sample")
})

test_that("a missing snapshot is an actionable error", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  expect_error(
    check_id(
      "MONDO:0005148",
      source_db = "mondo",
      how = "cache",
      version = "2099-01"
    ),
    class = "biogate_error_missing_snapshot"
  )
})

test_that("biogate_cache_dir honours the environment override", {
  d <- withr::local_tempdir()
  withr::local_envvar(BIOGATE_CACHE_DIR = d)
  expect_identical(biogate_cache_dir(), d)
})

test_that("biogate_snapshots lists the bundled samples", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  snaps <- biogate_snapshots()
  expect_s3_class(snaps, "tbl_df")
  expect_true(all(
    c("source", "version", "n_ids", "location") %in% names(snaps)
  ))
  mondo_sample <- snaps[snaps$source == "mondo" & snaps$version == "sample", ]
  expect_identical(nrow(mondo_sample), 1L)
  expect_gt(mondo_sample$n_ids, 0L)
  expect_identical(mondo_sample$location, "bundled")
})

test_that("biogate_snapshots lists the new obo samples", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  snaps <- biogate_snapshots()
  bundled <- snaps$source[
    snaps$version == "sample" & snaps$location == "bundled"
  ]
  expect_true(all(
    c("bto", "cl", "doid", "hp", "mp", "pato", "so", "uberon") %in% bundled
  ))
})
