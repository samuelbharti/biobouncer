# The synthetic column generator: correctness, determinism, and fixture parity.

.no_repairable <- c("ec", "hgnc", "hgvs")

.load_column_fixture <- function(source_db) {
  path <- file.path(
    system.file("extdata", "fixtures", "columns", package = "biobouncer"),
    paste0(source_db, ".cases.jsonl")
  )
  lines <- readLines(path, warn = FALSE)
  lines <- lines[nzchar(trimws(lines))]
  lapply(lines, jsonlite::fromJSON, simplifyVector = FALSE)
}

test_that("synthesize_ids is deterministic", {
  for (s in sources()) {
    expect_identical(synthesize_ids(s), synthesize_ids(s))
  }
})

test_that("synthesize_ids labels are self-consistent with the checker", {
  for (s in sources()) {
    gen <- synthesize_ids(s)
    for (i in seq_len(nrow(gen))) {
      res <- check_id(gen$input[i], source_db = s, how = "pattern")
      expected_cat <- if (isTRUE(res$valid[1])) {
        "valid"
      } else if (is.na(res$valid[1])) {
        "missing"
      } else if (!is.na(res$suggestion[1])) {
        "repairable"
      } else {
        "invalid"
      }
      expect_identical(gen$category[i], expected_cat)
      expect_identical(gen$valid[i], res$valid[1])
      expect_identical(gen$suggestion[i], res$suggestion[1])
    }
  }
})

test_that("synthesize_ids covers the expected categories", {
  for (s in sources()) {
    cats <- unique(synthesize_ids(s)$category)
    expect_true(all(c("valid", "invalid", "missing") %in% cats))
    if (s %in% .no_repairable) {
      expect_false("repairable" %in% cats)
    } else {
      expect_true("repairable" %in% cats)
    }
  }
})

test_that("synthesize_ids reproduces the committed fixtures", {
  # The Python generator writes the committed fixtures; R must reproduce them
  # element for element. This is the cross-language parity gate.
  for (s in sources()) {
    fx <- .load_column_fixture(s)
    gen <- synthesize_ids(s)
    expect_identical(nrow(gen), length(fx))
    for (i in seq_along(fx)) {
      fi <- fx[[i]]
      inp <- if (is.null(fi$input)) NA_character_ else fi$input
      vld <- if (is.null(fi$expect$valid)) NA else fi$expect$valid
      nrm <- if (is.null(fi$expect$normalized)) {
        NA_character_
      } else {
        fi$expect$normalized
      }
      sug <- if (is.null(fi$expect$suggestion)) {
        NA_character_
      } else {
        fi$expect$suggestion
      }
      expect_identical(gen$input[i], inp)
      expect_identical(gen$category[i], fi$category)
      expect_identical(gen$valid[i], vld)
      expect_identical(gen$normalized[i], nrm)
      expect_identical(gen$suggestion[i], sug)
    }
  }
})

test_that("synthesize_ids rejects an unknown source", {
  expect_error(
    synthesize_ids("not_a_source"),
    class = "biobouncer_error_unknown_source"
  )
})
