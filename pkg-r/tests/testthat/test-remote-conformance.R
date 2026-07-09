# Cross-language conformance for remote mode. The default run is backed by the
# recorded fixtures; the live run is opt-in via BIOGATE_REMOTE_TESTS.

.remote_corpus_files <- function() {
  dir <- system.file("extdata", "corpus", "remote", package = "biogate")
  sort(list.files(dir, pattern = "\\.jsonl$", full.names = TRUE))
}

.check_remote_corpus <- function(label) {
  files <- .remote_corpus_files()
  expect_gt(length(files), 0)
  n_cases <- 0
  for (f in files) {
    lines <- readLines(f, warn = FALSE)
    lines <- lines[nzchar(trimws(lines))]
    for (line in lines) {
      case <- jsonlite::fromJSON(line, simplifyVector = FALSE)
      res <- check_id(case$input, source_db = case$source_db, how = "remote")
      exp <- case$expect
      exp_norm <- if (is.null(exp$normalized)) NA_character_ else exp$normalized
      exp_sugg <- if (is.null(exp$suggestion)) NA_character_ else exp$suggestion
      info <- sprintf("%s %s: %s", case$source_db, label, case$input)
      expect_identical(res$valid, exp$valid, info = info)
      expect_identical(res$normalized, exp_norm, info = info)
      expect_identical(res$suggestion, exp_sugg, info = info)
      n_cases <- n_cases + 1
    }
  }
  expect_gt(n_cases, 0)
}

# Map a request url to the resolver, subkey, and id that name its fixture.
.fixture_route <- function(url) {
  ols <- regmatches(
    url,
    regexec("ontologies/([^/]+)/terms\\?obo_id=(.+)$", url)
  )[[1]]
  if (length(ols) == 3L) {
    return(list(resolver = "ols", subkey = ols[2], id = ols[3]))
  }
  ens <- regmatches(url, regexec("lookup/id/([^?]+)", url))[[1]]
  if (length(ens) == 2L) {
    return(list(resolver = "ensembl", subkey = "id", id = ens[2]))
  }
  uni <- regmatches(url, regexec("uniprotkb/([^.?/]+)", url))[[1]]
  if (length(uni) == 2L) {
    return(list(resolver = "uniprot", subkey = "uniprotkb", id = uni[2]))
  }
  stop("could not parse resolver and id from url: ", url)
}

# Serve recorded fixtures in place of the live API. A missing fixture must fail
# loudly rather than silently reach the network.
.fixture_transport <- function(url, timeout) {
  route <- .fixture_route(url)
  fx_path <- system.file(
    "extdata",
    "fixtures",
    "remote",
    route$resolver,
    route$subkey,
    paste0(gsub(":", "_", route$id), ".json"),
    package = "biogate"
  )
  if (!nzchar(fx_path) || !file.exists(fx_path)) {
    stop("missing fixture for ", route$resolver, " ", route$id)
  }
  fx <- jsonlite::fromJSON(fx_path, simplifyVector = FALSE)
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
  .check_remote_corpus("remote live")
})
