# Load source definitions from the vendored shared spec.

.biogate_cache <- new.env(parent = emptyenv())

.load_sources <- function() {
  if (!is.null(.biogate_cache$sources)) {
    return(.biogate_cache$sources)
  }
  dir <- system.file("extdata", "sources", package = "biogate")
  files <- sort(list.files(dir, pattern = "\\.yaml$", full.names = TRUE))
  reg <- list()
  for (f in files) {
    spec <- yaml::read_yaml(f)
    reg[[spec$key]] <- spec
  }
  .biogate_cache$sources <- reg
  reg
}

#' List available source databases
#'
#' @return A character vector of source keys, sorted.
#' @seealso [source_info()] for a table with more detail.
#' @examples
#' sources()
#' @export
sources <- function() {
  sort(names(.load_sources()))
}

.source_modes <- function(spec) {
  modes <- "pattern"
  if (!is.null(spec$cache)) {
    modes <- c(modes, "cache")
  }
  if (!is.null(spec$remote)) {
    modes <- c(modes, "remote")
  }
  paste(modes, collapse = ", ")
}

#' Describe the available sources
#'
#' Answers "what does a valid id look like and how can I check it?" for each
#' source.
#'
#' @return A [tibble][tibble::tibble] with one row per source and the columns
#'   `key`, `name`, `example` (a valid identifier for the source), `modes` (the
#'   checking modes it supports), `species_aware`, and `version_aware`.
#' @examples
#' source_info()
#' @export
source_info <- function() {
  reg <- .load_sources()
  keys <- sort(names(reg))
  tibble::tibble(
    key = keys,
    name = vapply(
      keys,
      function(k) reg[[k]]$name,
      character(1),
      USE.NAMES = FALSE
    ),
    example = vapply(
      keys,
      function(k) {
        ex <- reg[[k]]$example
        if (is.null(ex)) NA_character_ else ex
      },
      character(1),
      USE.NAMES = FALSE
    ),
    modes = vapply(
      keys,
      function(k) .source_modes(reg[[k]]),
      character(1),
      USE.NAMES = FALSE
    ),
    species_aware = vapply(
      keys,
      function(k) isTRUE(reg[[k]]$species_aware),
      logical(1),
      USE.NAMES = FALSE
    ),
    version_aware = vapply(
      keys,
      function(k) isTRUE(reg[[k]]$version_aware),
      logical(1),
      USE.NAMES = FALSE
    )
  )
}

.get_source <- function(source_db) {
  reg <- .load_sources()
  if (!source_db %in% names(reg)) {
    cli::cli_abort(
      c(
        "Unknown {.arg source_db} {.val {source_db}}.",
        i = "Available sources: {.val {sources()}}."
      ),
      class = "biogate_error_unknown_source"
    )
  }
  reg[[source_db]]
}
