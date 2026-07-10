# Offline tests for remote mode. The biogate.remote_transport option replaces
# the network seam so no request ever leaves the machine.

.stub_present <- function(present_ids) {
  function(url, timeout) {
    id <- sub(".*obo_id=", "", url)
    if (id %in% present_ids) {
      list(status = 200, body = list(page = list(totalElements = 1)))
    } else {
      list(status = 404, body = NULL)
    }
  }
}

# Ensembl answers 200 for a known id and 400 for a well-formed but unknown one.
.stub_ensembl <- function(present_ids) {
  function(url, timeout) {
    id <- sub(".*lookup/id/([^?]+).*", "\\1", url)
    if (id %in% present_ids) {
      list(status = 200, body = NULL)
    } else {
      list(status = 400, body = NULL)
    }
  }
}

# UniProt maps each known accession to an entryType; an unknown one is a 404.
.stub_uniprot <- function(entries) {
  function(url, timeout) {
    acc <- sub(".*uniprotkb/([^.?/]+).*", "\\1", url)
    if (acc %in% names(entries)) {
      list(status = 200, body = list(entryType = entries[[acc]]))
    } else {
      list(status = 404, body = NULL)
    }
  }
}

test_that("well-formed ids are valid when they exist remotely", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )

  res <- check_id(
    c("MONDO:0005148", "MONDO:9999999"),
    source_db = "mondo",
    how = "remote"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$normalized, c("MONDO:0005148", NA_character_))
  expect_identical(res$suggestion, c(NA_character_, NA_character_))
  expect_true(all(nzchar(res$version)))
})

test_that("a malformed input suggests a corrected id that exists remotely", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )

  res <- check_id("mondo:5148", source_db = "mondo", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "MONDO:0005148")
})

test_that("a source with no resolver errors with a classed condition", {
  expect_error(
    .get_resolver(list(key = "none")),
    class = "biogate_error_no_resolver"
  )
  expect_error(
    .get_resolver(list(key = "none", remote = list(resolver = "unknown"))),
    class = "biogate_error_no_resolver"
  )
})

test_that("an unexpected remote status raises a remote error", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      list(status = 500, body = NULL)
    }
  )
  expect_error(
    check_id("MONDO:0005148", source_db = "mondo", how = "remote"),
    class = "biogate_error_remote"
  )
  # An indeterminate status must not be cached.
  expect_false(file.exists(.remote_cache_path("ols", "mondo", "MONDO:0005148")))
})

test_that("ensembl ids resolve against the lookup endpoint", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_ensembl("ENSG00000139618")
  )

  res <- check_id(
    c("ENSG00000139618", "ENSG00000000000"),
    source_db = "ensembl",
    how = "remote"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$normalized, c("ENSG00000139618", NA_character_))
  expect_identical(res$suggestion, c(NA_character_, NA_character_))
})

test_that("a malformed ensembl id suggests a corrected id that exists remotely", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_ensembl("ENSG00000139618")
  )

  res <- check_id("ensg00000139618", source_db = "ensembl", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "ENSG00000139618")
})

test_that("uniprot accessions are valid only when the entry is active", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_uniprot(list(
      P01308 = "UniProtKB reviewed (Swiss-Prot)",
      O99999 = "Inactive"
    ))
  )

  res <- check_id(
    c("P01308", "O99999"),
    source_db = "uniprot",
    how = "remote"
  )
  expect_identical(res$valid, c(TRUE, FALSE))
  expect_identical(res$normalized, c("P01308", NA_character_))
  expect_identical(res$suggestion, c(NA_character_, NA_character_))
})

test_that("a malformed uniprot accession suggests an active corrected id", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_uniprot(list(
      P01308 = "UniProtKB reviewed (Swiss-Prot)"
    ))
  )

  res <- check_id("p01308", source_db = "uniprot", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "P01308")
})

test_that("unexpected ensembl and uniprot statuses raise a remote error", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  withr::with_options(
    list(
      biogate.remote_transport = function(url, timeout) {
        list(status = 500, body = NULL)
      }
    ),
    expect_error(
      check_id("ENSG00000139618", source_db = "ensembl", how = "remote"),
      class = "biogate_error_remote"
    )
  )
  expect_false(file.exists(.remote_cache_path(
    "ensembl",
    "id",
    "ENSG00000139618"
  )))

  withr::with_options(
    list(
      biogate.remote_transport = function(url, timeout) {
        list(status = 503, body = NULL)
      }
    ),
    expect_error(
      check_id("P01308", source_db = "uniprot", how = "remote"),
      class = "biogate_error_remote"
    )
  )
  expect_false(file.exists(.remote_cache_path(
    "uniprot",
    "uniprotkb",
    "P01308"
  )))
})

test_that("an on-disk cached response short-circuits the network", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines('{"status":200,"body":{"page":{"totalElements":1}}}', path)

  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "MONDO:0005148")
})

test_that("a corrupt cached response is ignored and refetched", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines("{ this is not valid json", path)

  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
})

test_that("a cache file without a status is ignored and refetched", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines('{"body":{"page":{"totalElements":1}}}', path)

  withr::local_options(
    biogate.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
})

test_that("ensembl and uniprot verdicts round-trip through the cache", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  withr::local_options(
    biogate.remote_transport = .stub_ensembl("ENSG00000139618")
  )
  expect_true(
    check_id("ENSG00000139618", source_db = "ensembl", how = "remote")$valid
  )

  withr::local_options(
    biogate.remote_transport = .stub_uniprot(list(
      P01308 = "UniProtKB reviewed (Swiss-Prot)",
      O99999 = "Inactive"
    ))
  )
  expect_true(check_id("P01308", source_db = "uniprot", how = "remote")$valid)
  expect_false(check_id("O99999", source_db = "uniprot", how = "remote")$valid)

  # A second lookup must come from the cache and never touch the network.
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  expect_true(
    check_id("ENSG00000139618", source_db = "ensembl", how = "remote")$valid
  )
  expect_true(check_id("P01308", source_db = "uniprot", how = "remote")$valid)
  expect_false(check_id("O99999", source_db = "uniprot", how = "remote")$valid)
})

test_that(".remote_parse_body tolerates empty and non-json input", {
  expect_null(.remote_parse_body(""))
  expect_null(.remote_parse_body("<html>Bad Gateway</html>"))
  parsed <- .remote_parse_body('{"page":{"totalElements":2}}')
  expect_equal(parsed$page$totalElements, 2)
})

test_that(".ols_count returns 0 for missing, null, or malformed counts", {
  expect_identical(.ols_count(NULL), 0L)
  expect_identical(.ols_count(list(page = list())), 0L)
  expect_identical(.ols_count(list(page = list(totalElements = 3))), 3L)
})
