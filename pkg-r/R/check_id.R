#' Check biological identifiers
#'
#' Validate a vector of identifiers against a source. Only offline `pattern`
#' mode is implemented so far.
#'
#' @param x A character vector of identifiers.
#' @param source_db Source key, for example `"mondo"`. See [sources()].
#' @param how Checking mode. Only `"pattern"` is implemented.
#' @param species Optional species context, echoed in the result.
#' @param version Optional version context. Ignored in `pattern` mode.
#' @return A data frame with one row per element of `x` and columns `input`,
#'   `valid`, `normalized`, `suggestion`, `source_db`, `version`, `species`,
#'   and `how`.
#' @examples
#' check_id(c("MONDO:0005148", "mondo:5148"), source_db = "mondo")
#' @export
check_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL
) {
  if (!identical(how, "pattern")) {
    stop(
      sprintf("Unsupported mode how = '%s'. Implemented modes: pattern.", how),
      call. = FALSE
    )
  }
  source <- .get_source(source_db)
  x <- as.character(x)
  n <- length(x)
  valid <- .matches(source$pattern, x)
  normalized <- ifelse(!is.na(valid) & valid, x, NA_character_)
  suggestion <- rep(NA_character_, n)
  for (i in which(!is.na(valid) & !valid)) {
    suggestion[i] <- .suggest_one(source, x[i])
  }
  species_col <- if (is.null(species)) NA_character_ else as.character(species)
  data.frame(
    input = x,
    valid = valid,
    normalized = normalized,
    suggestion = suggestion,
    source_db = rep(source_db, n),
    version = rep(NA_character_, n),
    species = rep(species_col, n),
    how = rep("pattern", n),
    stringsAsFactors = FALSE
  )
}

#' Test biological identifiers
#'
#' A convenience wrapper over [check_id()] that returns only the verdict.
#'
#' @inheritParams check_id
#' @return A logical vector, one element per element of `x`.
#' @examples
#' is_valid_id(c("MONDO:0005148", "mondo:5148"), source_db = "mondo")
#' @export
is_valid_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL
) {
  check_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version
  )$valid
}
