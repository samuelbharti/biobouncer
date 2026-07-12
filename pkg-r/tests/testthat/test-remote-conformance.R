# Cross-language conformance for remote mode. The default run is backed by the
# recorded fixtures; the live run is opt-in via BIOBOUNCER_REMOTE_TESTS.

.remote_corpus_files <- function() {
  dir <- system.file("extdata", "corpus", "remote", package = "biobouncer")
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

# Build a fixture-path index once by walking the vendored fixtures tree, keyed by
# (url, id). A GET fixture has no id and is keyed by URL; the URL encodes the
# query. A GraphQL/POST fixture (Open Targets) shares one endpoint URL across ids,
# so it is keyed by its id too, matched from the request body at replay time.
.fixture_key <- function(url, id) {
  if (is.null(id)) url else paste(url, id, sep = "\n")
}

.fixture_index <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      root <- system.file(
        "extdata",
        "fixtures",
        "remote",
        package = "biobouncer"
      )
      paths <- list.files(
        root,
        pattern = "\\.json$",
        recursive = TRUE,
        full.names = TRUE
      )
      idx <- list()
      for (p in paths) {
        fx <- jsonlite::fromJSON(p, simplifyVector = FALSE)
        idx[[.fixture_key(fx$url, fx$id)]] <- p
      }
      cache <<- idx
    }
    cache
  }
})

.fixture_serve <- function(url, id) {
  path <- .fixture_index()[[.fixture_key(url, id)]]
  if (is.null(path)) {
    stop(
      "missing fixture for url: ",
      url,
      " id: ",
      if (is.null(id)) "NA" else id
    )
  }
  fx <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  list(status = fx$status, body = fx$body)
}

# Serve recorded fixtures in place of the live API. A missing fixture must fail
# loudly rather than silently reach the network.
.fixture_transport <- function(url, timeout) {
  .fixture_serve(url, NULL)
}

# GraphQL fixtures are matched by the id carried in the POST body.
.fixture_transport_post <- function(url, body, timeout) {
  id <- jsonlite::fromJSON(body)$variables$ensemblId
  .fixture_serve(url, id)
}

test_that("remote conformance corpus passes against recorded fixtures", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biobouncer.remote_transport = .fixture_transport,
    biobouncer.remote_transport_post = .fixture_transport_post
  )
  .check_remote_corpus("remote")
})

test_that("remote conformance corpus passes against the live API", {
  skip_if(Sys.getenv("BIOBOUNCER_REMOTE_TESTS") == "")
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  .check_remote_corpus("remote live", live = TRUE)
})
