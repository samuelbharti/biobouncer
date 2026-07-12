# Cross-language conformance for remote mode. The default run is backed by the
# recorded fixtures; the live run is opt-in via BIOGATE_REMOTE_TESTS.

.remote_corpus_files <- function() {
  dir <- system.file("extdata", "corpus", "remote", package = "biogate")
  sort(list.files(dir, pattern = "\\.jsonl$", full.names = TRUE))
}

.check_remote_corpus <- function(label, live = FALSE) {
  files <- .remote_corpus_files()
  expect_gt(length(files), 0)
  n_cases <- 0
  for (f in files) {
    lines <- readLines(f, warn = FALSE)
    lines <- lines[nzchar(trimws(lines))]
    for (line in lines) {
      case <- jsonlite::fromJSON(line, simplifyVector = FALSE)
      # A simulated failure cannot be reproduced against the live API.
      if (live && isTRUE(case$offline_only)) {
        next
      }
      res <- check_id(
        case$input,
        source_db = case$source_db,
        how = "remote",
        species = case$species,
        on_error = if (is.null(case$on_error)) "raise" else case$on_error
      )
      exp <- case$expect
      exp_valid <- if (is.null(exp$valid)) NA else exp$valid
      exp_norm <- if (is.null(exp$normalized)) NA_character_ else exp$normalized
      exp_sugg <- if (is.null(exp$suggestion)) NA_character_ else exp$suggestion
      info <- sprintf("%s %s: %s", case$source_db, label, case$input)
      expect_identical(res$valid, exp_valid, info = info)
      expect_identical(res$normalized, exp_norm, info = info)
      expect_identical(res$suggestion, exp_sugg, info = info)
      # An indeterminate case carries an error; every other case must not.
      if (isTRUE(exp$error)) {
        expect_false(is.na(res$error), info = info)
      } else {
        expect_true(is.na(res$error), info = info)
      }
      n_cases <- n_cases + 1
    }
  }
  expect_gt(n_cases, 0)
}

# Build a url -> fixture-path index once by walking the vendored fixtures tree.
# Every fixture records the exact URL its resolver builds, so serving one is a
# direct lookup, with no per-resolver URL parsing to keep in sync.
.fixture_index <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      root <- system.file("extdata", "fixtures", "remote", package = "biogate")
      paths <- list.files(
        root,
        pattern = "\\.json$",
        recursive = TRUE,
        full.names = TRUE
      )
      idx <- list()
      for (p in paths) {
        fx <- jsonlite::fromJSON(p, simplifyVector = FALSE)
        idx[[fx$url]] <- p
      }
      cache <<- idx
    }
    cache
  }
})

# Serve recorded fixtures in place of the live API. A missing fixture must fail
# loudly rather than silently reach the network.
.fixture_transport <- function(url, timeout) {
  path <- .fixture_index()[[url]]
  if (is.null(path)) {
    stop("missing fixture for url: ", url)
  }
  fx <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  list(status = fx$status, body = fx$body)
}

test_that("remote conformance corpus passes against recorded fixtures", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(biogate.remote_transport = .fixture_transport)
  .check_remote_corpus("remote")
})

test_that("remote conformance corpus passes against the live API", {
  skip_if(Sys.getenv("BIOGATE_REMOTE_TESTS") == "")
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  .check_remote_corpus("remote live", live = TRUE)
})
