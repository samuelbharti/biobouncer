test_that("cross-language conformance corpus passes", {
  skip_if_not_installed("jsonlite")
  # Isolate the cache dir so cache cases resolve to the bundled sample snapshot.
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())

  dir <- system.file("extdata", "corpus", package = "biogate")
  files <- sort(list.files(dir, pattern = "\\.jsonl$", full.names = TRUE))
  expect_gt(length(files), 0)

  n_cases <- 0
  for (f in files) {
    lines <- readLines(f, warn = FALSE)
    lines <- lines[nzchar(trimws(lines))]
    for (line in lines) {
      case <- jsonlite::fromJSON(line, simplifyVector = FALSE)
      res <- check_id(
        case$input,
        source_db = case$source_db,
        how = case$how,
        version = case$version
      )
      exp <- case$expect
      exp_norm <- if (is.null(exp$normalized)) NA_character_ else exp$normalized
      exp_sugg <- if (is.null(exp$suggestion)) NA_character_ else exp$suggestion
      info <- sprintf("%s %s: %s", case$source_db, case$how, case$input)
      expect_identical(res$valid, exp$valid, info = info)
      expect_identical(res$normalized, exp_norm, info = info)
      expect_identical(res$suggestion, exp_sugg, info = info)
      n_cases <- n_cases + 1
    }
  }
  expect_gt(n_cases, 0)
})
