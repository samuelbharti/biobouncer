# Offline tests for remote mode. The biobouncer.remote_transport option replaces
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
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
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
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )

  res <- check_id("mondo:5148", source_db = "mondo", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "MONDO:0005148")
})

test_that("a source with no resolver errors with a classed condition", {
  expect_error(
    .get_resolver(list(key = "none")),
    class = "biobouncer_error_no_resolver"
  )
  expect_error(
    .get_resolver(list(key = "none", remote = list(resolver = "unknown"))),
    class = "biobouncer_error_no_resolver"
  )
})

test_that("an unexpected remote status raises a remote error", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      list(status = 500, body = NULL)
    }
  )
  expect_error(
    check_id("MONDO:0005148", source_db = "mondo", how = "remote"),
    class = "biobouncer_error_remote"
  )
  # An indeterminate status must not be cached.
  expect_false(file.exists(.remote_cache_path("ols", "mondo", "MONDO:0005148")))
})

test_that("ensembl ids resolve against the lookup endpoint", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_ensembl("ENSG00000139618")
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
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_ensembl("ENSG00000139618")
  )

  res <- check_id("ensg00000139618", source_db = "ensembl", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "ENSG00000139618")
})

test_that("uniprot accessions are valid only when the entry is active", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_uniprot(list(
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
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_uniprot(list(
      P01308 = "UniProtKB reviewed (Swiss-Prot)"
    ))
  )

  res <- check_id("p01308", source_db = "uniprot", how = "remote")
  expect_false(res$valid)
  expect_true(is.na(res$normalized))
  expect_identical(res$suggestion, "P01308")
})

test_that("unexpected ensembl and uniprot statuses raise a remote error", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())

  withr::with_options(
    list(
      biobouncer.remote_transport = function(url, timeout) {
        list(status = 500, body = NULL)
      }
    ),
    expect_error(
      check_id("ENSG00000139618", source_db = "ensembl", how = "remote"),
      class = "biobouncer_error_remote"
    )
  )
  expect_false(file.exists(.remote_cache_path(
    "ensembl",
    "id",
    "ENSG00000139618"
  )))

  withr::with_options(
    list(
      biobouncer.remote_transport = function(url, timeout) {
        list(status = 503, body = NULL)
      }
    ),
    expect_error(
      check_id("P01308", source_db = "uniprot", how = "remote"),
      class = "biobouncer_error_remote"
    )
  )
  expect_false(file.exists(.remote_cache_path(
    "uniprot",
    "uniprotkb",
    "P01308"
  )))
})

test_that("an on-disk cached response short-circuits the network", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines('{"status":200,"body":{"page":{"totalElements":1}}}', path)

  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
  expect_identical(res$normalized, "MONDO:0005148")
})

test_that("a corrupt cached response is ignored and refetched", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines("{ this is not valid json", path)

  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
})

test_that("a cache file without a status is ignored and refetched", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines('{"body":{"page":{"totalElements":1}}}', path)

  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
})

test_that("ensembl and uniprot verdicts round-trip through the cache", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())

  withr::local_options(
    biobouncer.remote_transport = .stub_ensembl("ENSG00000139618")
  )
  expect_true(
    check_id("ENSG00000139618", source_db = "ensembl", how = "remote")$valid
  )

  withr::local_options(
    biobouncer.remote_transport = .stub_uniprot(list(
      P01308 = "UniProtKB reviewed (Swiss-Prot)",
      O99999 = "Inactive"
    ))
  )
  expect_true(check_id("P01308", source_db = "uniprot", how = "remote")$valid)
  expect_false(check_id("O99999", source_db = "uniprot", how = "remote")$valid)

  # A second lookup must come from the cache and never touch the network.
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
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

test_that("a fetch records its time and reports it as the version", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  record <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  expect_true(nzchar(record$fetched_at)) # the fetch time is in the cache record
  expect_identical(res$version, record$fetched_at) # and is the result version
})

test_that("a cached verdict reports its original fetch time", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(
    paste0(
      '{"status":200,"body":{"page":{"totalElements":1}},',
      '"url":"x","fetched_at":"2000-01-01T00:00:00Z"}'
    ),
    path
  )
  withr::local_options(
    biobouncer.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid)
  # The verdict came from the cache, so its version is the original fetch time.
  expect_identical(res$version, "2000-01-01T00:00:00Z")
})

test_that("refresh skips the cache and refetches", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(
    '{"status":404,"body":null,"url":"x","fetched_at":"2000-01-01T00:00:00Z"}',
    path
  )
  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )
  stale <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_false(stale$valid) # served from the cached "absent" record
  fresh <- check_id(
    "MONDO:0005148",
    source_db = "mondo",
    how = "remote",
    refresh = TRUE
  )
  expect_true(fresh$valid) # refetched, ignoring the cache
  expect_false(identical(fresh$version, "2000-01-01T00:00:00Z"))
})

test_that("a cached response older than the TTL is refetched", {
  withr::local_envvar(
    BIOBOUNCER_CACHE_DIR = withr::local_tempdir(),
    BIOBOUNCER_REMOTE_TTL = "1"
  )
  path <- .remote_cache_path("ols", "mondo", "MONDO:0005148")
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(
    '{"status":404,"body":null,"url":"x","fetched_at":"2000-01-01T00:00:00Z"}',
    path
  )
  withr::local_options(
    biobouncer.remote_transport = .stub_present("MONDO:0005148")
  )
  res <- check_id("MONDO:0005148", source_db = "mondo", how = "remote")
  expect_true(res$valid) # the record aged past the TTL, so it refetched
})

test_that(".remote_ttl reads the environment", {
  withr::local_envvar(BIOBOUNCER_REMOTE_TTL = "")
  expect_null(.remote_ttl())
  for (off in c("0", "-5", "not-a-number")) {
    withr::local_envvar(BIOBOUNCER_REMOTE_TTL = off)
    expect_null(.remote_ttl())
  }
  withr::local_envvar(BIOBOUNCER_REMOTE_TTL = "3600")
  expect_identical(.remote_ttl(), 3600)
})

test_that(".is_stale applies the ttl rules", {
  expect_false(.is_stale("2000-01-01T00:00:00Z", NULL)) # no ttl, never stale
  expect_true(.is_stale(NA_character_, 100)) # no timestamp to trust
  expect_true(.is_stale("garbage", 100)) # unparseable
  expect_true(.is_stale("2000-01-01T00:00:00Z", 100)) # long expired
  expect_false(.is_stale(.utc_stamp(), 3600)) # fresh
})

test_that(".remote_retry retries a transient result then returns the success", {
  calls <- 0L
  fetch <- function() {
    calls <<- calls + 1L
    if (calls < 3L) {
      list(status = 503L, body = NULL) # transient server error
    } else {
      list(status = 200L, body = NULL)
    }
  }
  resp <- .remote_retry(fetch, attempts = 3L, sleep = function(s) {
    invisible(NULL)
  })
  expect_identical(resp$status, 200L)
  expect_identical(calls, 3L) # two retries, then the success
})

test_that(".remote_retry gives up after the last attempt", {
  calls <- 0L
  fetch <- function() {
    calls <<- calls + 1L
    NULL # a caught network error
  }
  resp <- .remote_retry(fetch, attempts = 3L, sleep = function(s) {
    invisible(NULL)
  })
  expect_null(resp)
  expect_identical(calls, 3L)
})

test_that(".ncbi_suffix adds the key only when configured", {
  withr::local_envvar(NCBI_API_KEY = "", NCBI_EMAIL = "")
  expect_identical(.ncbi_suffix(), "") # no key, URL unchanged
  withr::local_envvar(NCBI_API_KEY = "secret")
  suffix <- .ncbi_suffix()
  expect_true(startsWith(suffix, "&"))
  expect_true(grepl("api_key=secret", suffix, fixed = TRUE))
  expect_true(grepl("tool=biobouncer", suffix, fixed = TRUE))
})
