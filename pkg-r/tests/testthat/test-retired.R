# Version retirement: remote OLS obsolete terms and cache retired sidecars.

test_that(".normalize_obo turns short forms and IRIs into colon obo_ids", {
  expect_identical(.normalize_obo("GO_0006915"), "GO:0006915")
  expect_identical(
    .normalize_obo("http://purl.obolibrary.org/obo/MONDO_0005016"),
    "MONDO:0005016"
  )
  expect_null(.normalize_obo(NULL))
  expect_null(.normalize_obo(""))
})

# An OLS transport stub that serves one obsolete term with the given successor.
.stub_obsolete <- function(replaced_by) {
  function(url, timeout) {
    list(
      status = 200,
      body = list(
        page = list(totalElements = 1),
        "_embedded" = list(
          terms = list(list(
            is_obsolete = TRUE,
            term_replaced_by = replaced_by
          ))
        )
      )
    )
  }
}

test_that("remote mode marks an obsolete term invalid with its successor", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .stub_obsolete("GO_0006915"))

  res <- check_id("GO:0006917", source_db = "go", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "GO:0006915")
})

test_that("remote mode surfaces a cross-ontology successor from a full IRI", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_obsolete(
      "http://purl.obolibrary.org/obo/MONDO_0005016"
    )
  )

  res <- check_id("EFO:0000401", source_db = "efo", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "MONDO:0005016")
})

test_that("cache mode marks a retired id invalid with its successor", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  res <- check_id(
    "GO:0006917",
    source_db = "go",
    how = "cache",
    version = "sample"
  )
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "GO:0006915")
})

test_that("a well-formed id neither in the snapshot nor retired has no suggestion", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  res <- check_id(
    "GO:0000001",
    source_db = "go",
    how = "cache",
    version = "sample"
  )
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that(".snapshot_retired reads the bundled go retired sidecar", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  retired <- .snapshot_retired("go", "sample")
  expect_true("GO:0006917" %in% names(retired))
  expect_identical(retired[["GO:0006917"]], "GO:0006915")
})

test_that(".snapshot_retired returns an empty named vector with no sidecar", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  retired <- .snapshot_retired("mondo", "sample")
  expect_identical(length(retired), 0L)
  expect_identical(names(retired), character(0))
})
