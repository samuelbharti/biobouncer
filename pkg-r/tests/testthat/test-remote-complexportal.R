# Offline tests for complexportal remote mode. Existence is checked against the
# EBI Complex Portal web service; the biobouncer.remote_transport option replaces it.

.stub_complexportal <- function(status, body = NULL) {
  function(url, timeout) list(status = status, body = body)
}

test_that("the url addresses the complex endpoint", {
  url <- .remote_resolvers$complexportal$url(NULL, "CPX-2158")
  expect_identical(
    url,
    "https://www.ebi.ac.uk/intact/complex-ws/complex/CPX-2158"
  )
})

test_that("an existing complex is valid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_complexportal(200))
  res <- check_id("CPX-2158", "complexportal", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "CPX-2158")
  expect_true(is.na(res$suggestion))
})

test_that("an absent complex is invalid", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_complexportal(404))
  res <- check_id("CPX-9999999", "complexportal", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("a lowercase id suggests the uppercase form", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_complexportal(200))
  res <- check_id("cpx-2158", "complexportal", how = "remote")
  expect_false(res$valid)
  expect_identical(res$suggestion, "CPX-2158")
})

test_that("a malformed id skips the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("a malformed id must not reach the network")
    }
  )
  res <- check_id("CPX-XYZ", "complexportal", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$suggestion))
})

test_that("an unexpected status raises and is not cached", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biobouncer.remote_transport = .stub_complexportal(500))
  expect_error(
    check_id("CPX-2158", "complexportal", how = "remote"),
    class = "biobouncer_error_remote"
  )
  expect_false(
    file.exists(.remote_cache_path("complexportal", "complex", "CPX-2158"))
  )
})
