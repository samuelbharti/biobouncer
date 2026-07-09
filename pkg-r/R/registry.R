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
#' @examples
#' sources()
#' @export
sources <- function() {
  sort(names(.load_sources()))
}

.get_source <- function(source_db) {
  reg <- .load_sources()
  if (!source_db %in% names(reg)) {
    stop(
      sprintf(
        "Unknown source_db '%s'. Available: %s.",
        source_db,
        paste(sources(), collapse = ", ")
      ),
      call. = FALSE
    )
  }
  reg[[source_db]]
}
