# Generate a synthetic, labeled column of identifiers for any source. This mirrors
# the Python biobouncer.synthesize element for element, so both languages produce
# identical columns; the committed fixtures under inst/extdata/fixtures/columns are
# the shared parity gate. Every value is labeled by running the pattern-mode
# checker, so the categories are always correct.

.synth_categories <- c("valid", "repairable", "invalid", "missing")

# Characters guaranteed to be outside every source pattern, used to turn a valid
# id into a hard invalid.
.synth_breakers <- c("!", " x", "##")

.increment_last_digit_run <- function(s, delta) {
  m <- gregexpr("[0-9]+", s, perl = TRUE)[[1]]
  if (length(m) == 1L && m[1] == -1L) {
    return(NA_character_)
  }
  starts <- as.integer(m)
  lens <- attr(m, "match.length")
  i <- length(starts)
  start <- starts[i]
  len <- lens[i]
  run <- substr(s, start, start + len - 1L)
  value <- as.numeric(run) + delta
  if (value < 0) {
    return(NA_character_)
  }
  rep <- sprintf("%.0f", value)
  if (nchar(rep) < len) {
    rep <- paste0(strrep("0", len - nchar(rep)), rep)
  }
  paste0(substr(s, 1L, start - 1L), rep, substr(s, start + len, nchar(s)))
}

.synth_valid_values <- function(spec, n, seed) {
  values <- spec$example
  if (n >= 2) {
    for (i in seq_len(n - 1L)) {
      candidate <- .increment_last_digit_run(spec$example, i + seed)
      if (!is.na(candidate) && !(candidate %in% values)) {
        values <- c(values, candidate)
      }
    }
  }
  values
}

.synth_repairable_values <- function(spec) {
  example <- spec$example
  candidates <- character(0)
  if (!is.null(spec$curie)) {
    idx <- regexpr(":", example, fixed = TRUE)
    if (idx > 0L) {
      head <- substr(example, 1L, idx - 1L)
      local <- substr(example, idx + 1L, nchar(example))
      if (tolower(head) != head) {
        candidates <- c(candidates, paste0(tolower(head), ":", local))
      }
      if (!is.null(spec$curie$pad_to) && grepl("^[0-9]+$", local)) {
        stripped <- sub("^0+", "", local)
        if (!nzchar(stripped)) {
          stripped <- "0"
        }
        if (stripped != local) {
          candidates <- c(candidates, paste0(head, ":", stripped))
        }
      }
    }
    return(candidates)
  }
  case <- if (!is.null(spec$normalize)) spec$normalize$case else NULL
  if (!is.null(case) && case == "upper" && tolower(example) != example) {
    candidates <- c(candidates, tolower(example))
  } else if (!is.null(case) && case == "lower" && toupper(example) != example) {
    candidates <- c(candidates, toupper(example))
  }
  candidates
}

.synth_invalid_values <- function(spec, n) {
  paste0(
    spec$example,
    .synth_breakers[seq_len(min(n, length(.synth_breakers)))]
  )
}

.synth_category <- function(valid, suggestion) {
  if (isTRUE(valid)) {
    return("valid")
  }
  if (is.na(valid)) {
    return("missing")
  }
  if (!is.na(suggestion)) {
    return("repairable")
  }
  "invalid"
}

.synth_row <- function(source_db, value) {
  res <- check_id(value, source_db = source_db, how = "pattern")
  list(
    input = res$input[1],
    category = .synth_category(res$valid[1], res$suggestion[1]),
    valid = res$valid[1],
    normalized = res$normalized[1],
    suggestion = res$suggestion[1]
  )
}

.synth_rows_for <- function(source_db, values, target, limit) {
  rows <- list()
  seen <- character(0)
  for (value in values) {
    key <- if (is.na(value)) "missing" else value
    if (key %in% seen) {
      next
    }
    seen <- c(seen, key)
    row <- .synth_row(source_db, value)
    if (identical(row$category, target)) {
      rows[[length(rows) + 1L]] <- row
    }
    if (length(rows) >= limit) {
      break
    }
  }
  rows
}

.synth_interleave <- function(buckets) {
  ordered <- buckets[.synth_categories]
  depth <- max(vapply(ordered, length, integer(1)), 0L)
  out <- list()
  for (i in seq_len(depth)) {
    for (bucket in ordered) {
      if (i <= length(bucket)) {
        out[[length(out) + 1L]] <- bucket[[i]]
      }
    }
  }
  out
}

#' Generate a synthetic column of identifiers
#'
#' `synthesize_ids()` builds a small "messy column" for a source: a mix of
#' well-formed ids, repairable ids (a wrong-case or unpadded form that suggests a
#' valid one), hard-invalid ids, and missing cells. Every value is labeled by
#' running the pattern-mode checker, so the labels are always correct and match
#' what the Python `synthesize()` produces for the same source. It is useful for
#' exercising a validation pipeline (feed the column to [report_id()],
#' [repair_id()], or an adapter) without hand-writing test data. The generation is
#' deterministic and offline.
#'
#' @param source_db Source key, for example `"mondo"`. See [sources()].
#' @param n_valid How many well-formed ids to include. A source with no numeric
#'   part yields just the example.
#' @param n_repairable How many repairable ids. `ec`, `hgvs`, and `hgnc` have no
#'   pattern-mode repairable form, so they yield none.
#' @param n_invalid How many hard-invalid ids (neither valid nor suggestible).
#' @param missing How many missing cells (`NA`).
#' @param seed Shifts the numeric variants, for a different but still deterministic
#'   column.
#' @return A [tibble][tibble::tibble] with the columns `input`, `category`
#'   (`"valid"`, `"repairable"`, `"invalid"`, or `"missing"`), and the pattern-mode
#'   `valid`, `normalized`, and `suggestion` for that input. Categories a source
#'   cannot produce are simply absent.
#' @seealso [report_id()], [check_id()].
#' @examples
#' synthesize_ids("mondo")
#' @export
synthesize_ids <- function(
  source_db,
  n_valid = 2,
  n_repairable = 1,
  n_invalid = 1,
  missing = 1,
  seed = 0
) {
  spec <- .get_source(source_db)
  buckets <- list(
    valid = .synth_rows_for(
      source_db,
      .synth_valid_values(spec, n_valid, seed),
      "valid",
      n_valid
    ),
    repairable = .synth_rows_for(
      source_db,
      .synth_repairable_values(spec),
      "repairable",
      n_repairable
    ),
    invalid = .synth_rows_for(
      source_db,
      .synth_invalid_values(spec, length(.synth_breakers)),
      "invalid",
      n_invalid
    ),
    missing = .synth_rows_for(
      source_db,
      rep(NA_character_, missing),
      "missing",
      missing
    )
  )
  rows <- .synth_interleave(buckets)
  chr <- function(field) {
    vapply(
      rows,
      function(r) {
        v <- r[[field]]
        if (is.null(v) || is.na(v)) NA_character_ else as.character(v)
      },
      character(1)
    )
  }
  tibble::tibble(
    input = chr("input"),
    category = vapply(rows, function(r) r$category, character(1)),
    valid = vapply(
      rows,
      function(r) if (is.null(r$valid)) NA else r$valid,
      logical(1)
    ),
    normalized = chr("normalized"),
    suggestion = chr("suggestion")
  )
}
