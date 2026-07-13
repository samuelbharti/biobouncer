# The single description of a serialized check result. Both packages read the
# field order and version from one vendored file (extdata/schema/result.json),
# so the R and Python serializations cannot drift. The report print and summary
# methods count results through .summarize_results(); nothing else should
# hand-build a result payload.

.result_schema <- function() {
  if (!is.null(.biobouncer_cache$schema)) {
    return(.biobouncer_cache$schema)
  }
  path <- system.file(
    "extdata",
    "schema",
    "result.json",
    package = "biobouncer"
  )
  schema <- jsonlite::fromJSON(path, simplifyVector = TRUE)
  .biobouncer_cache$schema <- schema
  schema
}

# The payload-shape label. Read it before the fields: it is bumped whenever a
# field is added, removed, or renamed.
.schema_version <- function() {
  as.character(.result_schema()$schema_version)
}

# The order of columns in one serialized result.
.result_fields <- function() {
  as.character(.result_schema()$result_fields)
}

# The set of counts a report summary reports.
.summary_fields <- function() {
  as.character(.result_schema()$summary_fields)
}

# Count a check_id tibble into the shared summary fields. total is
# valid + invalid + missing + indeterminate. repairable is the subset of invalid
# that carries a suggestion, so it is not added on top of the other counts. A
# valid-is-NA row is indeterminate when it carries an error (a value that could
# not be checked) and missing otherwise (an absent input).
.summarize_results <- function(tbl) {
  valid <- tbl$valid
  suggestion <- tbl$suggestion
  error <- tbl$error
  if (is.null(error)) {
    error <- rep(NA_character_, nrow(tbl))
  }
  na_valid <- is.na(valid)
  list(
    total = nrow(tbl),
    valid = sum(valid, na.rm = TRUE),
    invalid = sum(!valid, na.rm = TRUE),
    repairable = sum(!valid & !is.na(suggestion), na.rm = TRUE),
    missing = sum(na_valid & is.na(error)),
    indeterminate = sum(na_valid & !is.na(error))
  )
}
