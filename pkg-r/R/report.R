# Validate and repair a whole column in one call. report_id() classes the
# check_id() table so it prints with a summary; repair_id() returns a repaired
# vector for dplyr::mutate(). Both are thin wrappers over check_id(), so R and
# Python stay in lockstep through the conformance corpus.

#' Validate and report on a column of identifiers
#'
#' `report_id()` runs [check_id()] over a column and returns its result table
#' with the extra class `biogate_report`, so it prints with a one-line summary of
#' how many values are valid, repairable, invalid, or missing. It is the
#' recommended entry point for inspecting and cleaning a column. Use [repair_id()]
#' inside `dplyr::mutate()` to substitute the fixable values. For enforcing
#' validity inside a framework, reach for the adapters such as [id_predicate()].
#'
#' @inheritParams check_id
#' @return A [tibble][tibble::tibble], as returned by [check_id()], with the extra
#'   class `biogate_report`. Calling `summary()` on it returns a one-row tibble of
#'   counts.
#' @seealso [repair_id()], [check_id()].
#' @examples
#' report_id(c("MONDO:0005148", "mondo:5148"), "mondo")
#' @export
report_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL,
  refresh = FALSE,
  on_error = "raise"
) {
  res <- check_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version,
    refresh = refresh,
    on_error = on_error
  )
  class(res) <- c("biogate_report", class(res))
  res
}

#' Repair a column of identifiers
#'
#' Returns `x` with every fixable value substituted by its suggestion: an invalid
#' value that maps to a successor or a well-formed alternative. Valid values,
#' invalid values with no suggestion, and missing values are returned unchanged,
#' so the result is the same length and order as `x`. It is designed to drop into
#' `dplyr::mutate()`.
#'
#' @inheritParams check_id
#' @return A character vector the same length as `x`.
#' @seealso [report_id()], [check_id()].
#' @examples
#' repair_id(c("MONDO:0005148", "mondo:5148"), "mondo")
#' @export
repair_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL,
  refresh = FALSE,
  on_error = "raise"
) {
  res <- check_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version,
    refresh = refresh,
    on_error = on_error
  )
  repaired <- res$input
  fixable <- !is.na(res$valid) & !res$valid & !is.na(res$suggestion)
  repaired[fixable] <- res$suggestion[fixable]
  repaired
}

# Disjoint display buckets that sum to the total: valid, repairable (an invalid
# value with a suggestion), invalid (no suggestion), missing, and indeterminate.
.report_counts <- function(x) {
  counts <- .summarize_results(x)
  list(
    total = counts$total,
    valid = counts$valid,
    repairable = counts$repairable,
    invalid = counts$invalid - counts$repairable,
    missing = counts$missing,
    indeterminate = counts$indeterminate
  )
}

#' @param object A `biogate_report`, as returned by [report_id()].
#' @param ... Ignored.
#' @rdname report_id
#' @export
summary.biogate_report <- function(object, ...) {
  # Shared schema semantics, matching the Python Report.summary: invalid counts
  # every failed value, and repairable is the subset of those with a suggestion.
  counts <- .summarize_results(object)
  tibble::tibble(
    total = counts$total,
    valid = counts$valid,
    invalid = counts$invalid,
    repairable = counts$repairable,
    missing = counts$missing,
    indeterminate = counts$indeterminate
  )
}

#' @param x A `biogate_report`, as returned by [report_id()].
#' @rdname report_id
#' @export
print.biogate_report <- function(x, ...) {
  counts <- .report_counts(x)
  src <- if (nrow(x)) x$source_db[[1L]] else NA_character_
  how_mode <- if (nrow(x)) x$how[[1L]] else NA_character_
  parts <- sprintf(
    "%d valid, %d repairable, %d invalid, %d missing",
    counts$valid,
    counts$repairable,
    counts$invalid,
    counts$missing
  )
  if (counts$indeterminate > 0) {
    parts <- paste0(parts, sprintf(", %d indeterminate", counts$indeterminate))
  }
  cat(sprintf(
    "# biogate report on %s (%s mode): %s of %d\n",
    src,
    how_mode,
    parts,
    counts$total
  ))
  NextMethod()
  invisible(x)
}
