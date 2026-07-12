# The Open Targets resolver: the first GraphQL (POST) remote check. The test
# transport for POST receives the request body and reads the id from it.

.ot_post_stub <- function(covered) {
  function(url, body, timeout) {
    id <- jsonlite::fromJSON(body)$variables$ensemblId
    target <- if (id %in% covered) list(id = id) else NULL
    list(status = 200, body = list(data = list(target = target)))
  }
}

test_that("a covered Open Targets target is valid", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport_post = .ot_post_stub("ENSG00000139618")
  )
  res <- check_id("ENSG00000139618", source_db = "opentargets", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "ENSG00000139618")
})

test_that("a gene the platform does not cover is absent", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport_post = .ot_post_stub(character(0))
  )
  res <- check_id("ENSG00000000000", source_db = "opentargets", how = "remote")
  expect_false(res$valid)
})

test_that("a malformed case suggests the covered form", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport_post = .ot_post_stub("ENSG00000139618")
  )
  res <- check_id("ensg00000139618", source_db = "opentargets", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "ENSG00000139618")
})

test_that("an unexpected status is left indeterminate under on_error", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport_post = function(url, body, timeout) {
      list(status = 500, body = NULL)
    }
  )
  res <- check_id(
    "ENSG00000139618",
    source_db = "opentargets",
    how = "remote",
    on_error = "indeterminate"
  )
  expect_true(is.na(res$valid))
  expect_false(is.na(res$error))
})

test_that("opentargets is a registered source", {
  info <- source_info()
  row <- info[info$key == "opentargets", ]
  expect_identical(nrow(row), 1L)
  expect_identical(row$modes, "pattern, remote")
})
