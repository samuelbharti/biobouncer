# The single description of a serialized check result. Both packages read the
# field order and version from one vendored file (extdata/schema/result.json),
# so the R and Python serializations cannot drift. The report print and summary
# methods count results through .summarize_results(); nothing else should
# hand-build a result payload.

.result_schema <- function() {
  if (!is.null(.biogate_cache$schema)) {
    return(.biogate_cache$schema)
  }
  path <- system.file("extdata", "schema", "result.json", package = "biogate")
  schema <- jsonlite::fromJSON(path, simplifyVector = TRUE)
  .biogate_cache$schema <- schema
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
# valid + invalid + missing. repairable is the subset of invalid that carries a
# suggestion, so it is not added on top of the other counts. A missing input
# (valid is NA) is counted as missing, never as valid or invalid.
.summarize_results <- function(tbl) {
  valid <- tbl$valid
  suggestion <- tbl$suggestion
  list(
    total = nrow(tbl),
    valid = sum(valid, na.rm = TRUE),
    invalid = sum(!valid, na.rm = TRUE),
    repairable = sum(!valid & !is.na(suggestion), na.rm = TRUE),
    missing = sum(is.na(valid))
  )
}
