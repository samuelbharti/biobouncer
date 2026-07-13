# Per-source synthetic columns exercise report_id/repair_id and the adapters
# uniformly, so every source gets column-level coverage, not just mondo and hgnc.

.column_fixture <- function(source_db) {
  path <- file.path(
    system.file("extdata", "fixtures", "columns", package = "biobouncer"),
    paste0(source_db, ".cases.jsonl")
  )
  lines <- readLines(path, warn = FALSE)
  lines <- lines[nzchar(trimws(lines))]
  lapply(lines, jsonlite::fromJSON, simplifyVector = FALSE)
}

.fx_inputs <- function(fx) {
  vapply(
    fx,
    function(r) if (is.null(r$input)) NA_character_ else r$input,
    character(1)
  )
}

.fx_categories <- function(fx) {
  vapply(fx, function(r) r$category, character(1))
}

.fx_suggestions <- function(fx) {
  vapply(
    fx,
    function(r) {
      if (is.null(r$expect$suggestion)) NA_character_ else r$expect$suggestion
    },
    character(1)
  )
}

test_that("report_id summary matches the category tallies", {
  for (s in sources()) {
    fx <- .column_fixture(s)
    cats <- .fx_categories(fx)
    summ <- summary(report_id(.fx_inputs(fx), s, how = "pattern"))
    expect_equal(summ$total, length(fx))
    expect_equal(summ$valid, sum(cats == "valid"))
    expect_equal(summ$repairable, sum(cats == "repairable"))
    # invalid counts every failed value: the hard invalids plus the repairables.
    expect_equal(summ$invalid, sum(cats %in% c("invalid", "repairable")))
    expect_equal(summ$missing, sum(cats == "missing"))
    expect_equal(summ$indeterminate, 0)
  }
})

test_that("repair_id substitutes only the repairable cells", {
  for (s in sources()) {
    fx <- .column_fixture(s)
    cats <- .fx_categories(fx)
    inputs <- .fx_inputs(fx)
    expected <- ifelse(cats == "repairable", .fx_suggestions(fx), inputs)
    expect_identical(repair_id(inputs, s, how = "pattern"), expected)
  }
})

test_that("is_valid_id matches each cell category", {
  for (s in sources()) {
    fx <- .column_fixture(s)
    cats <- .fx_categories(fx)
    verdicts <- is_valid_id(.fx_inputs(fx), s, how = "pattern")
    expected <- ifelse(
      cats == "valid",
      TRUE,
      ifelse(cats == "missing", NA, FALSE)
    )
    expect_identical(verdicts, expected)
  }
})

test_that("the adapters flag repairable and invalid but pass a missing cell", {
  for (s in sources()) {
    fx <- .column_fixture(s)
    cats <- .fx_categories(fx)
    inputs <- .fx_inputs(fx)
    # id_predicate: TRUE for valid and missing (NA passes), FALSE for the rest.
    predicate <- id_predicate(s, how = "pattern")
    expect_identical(predicate(inputs), !(cats %in% c("repairable", "invalid")))
    # check_valid_id: a valid-only column with a missing cell passes; the messy
    # column always contains a hard invalid, so it returns a failure message.
    valids <- c(inputs[cats == "valid"], NA)
    expect_true(isTRUE(check_valid_id(valids, s, how = "pattern")))
    expect_type(check_valid_id(inputs, s, how = "pattern"), "character")
  }
})

.cache_col_sources <- function() {
  info <- source_info()
  info$key[grepl("cache", info$modes)]
}

.cache_column <- function(source_db) {
  path <- file.path(
    system.file("extdata", "fixtures", "columns", package = "biobouncer"),
    paste0(source_db, ".cache.jsonl")
  )
  lines <- readLines(path, warn = FALSE)
  lines <- lines[nzchar(trimws(lines))]
  lapply(lines, jsonlite::fromJSON, simplifyVector = FALSE)
}

test_that("report_id and repair_id work over a cache-mode column", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  for (s in .cache_col_sources()) {
    fx <- .cache_column(s)
    cats <- .fx_categories(fx)
    inputs <- .fx_inputs(fx)
    summ <- summary(report_id(inputs, s, how = "cache", version = "sample"))
    expect_equal(summ$valid, sum(cats == "valid"))
    expect_equal(summ$repairable, sum(cats == "repairable"))
    expect_equal(summ$invalid, sum(cats %in% c("invalid", "repairable")))
    expect_equal(summ$missing, sum(cats == "missing"))

    expected <- ifelse(cats == "repairable", .fx_suggestions(fx), inputs)
    expect_identical(
      repair_id(inputs, s, how = "cache", version = "sample"),
      expected
    )
  }
})

test_that("is_valid_id and the adapters work over a cache-mode column", {
  withr::local_envvar(BIOBOUNCER_CACHE_DIR = withr::local_tempdir())
  for (s in .cache_col_sources()) {
    fx <- .cache_column(s)
    cats <- .fx_categories(fx)
    inputs <- .fx_inputs(fx)
    verdicts <- is_valid_id(inputs, s, how = "cache", version = "sample")
    expected <- ifelse(
      cats == "valid",
      TRUE,
      ifelse(cats == "missing", NA, FALSE)
    )
    expect_identical(verdicts, expected)

    predicate <- id_predicate(s, how = "cache", version = "sample")
    expect_identical(predicate(inputs), !(cats %in% c("repairable", "invalid")))
  }
})
