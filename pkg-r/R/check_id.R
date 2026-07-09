.assert_check_args <- function(x, source_db, how, species, version) {
  checkmate::assert_atomic(x, .var.name = "x")
  checkmate::assert_string(source_db, .var.name = "source_db")
  checkmate::assert_string(how, .var.name = "how")
  if (!is.null(species)) {
    checkmate::assert_scalar(species, na.ok = FALSE, .var.name = "species")
  }
  if (!is.null(version)) {
    checkmate::assert_scalar(version, na.ok = FALSE, .var.name = "version")
  }
}

.assert_mode_supported <- function(how) {
  known <- c("pattern", "cache", "remote", "existence")
  if (!how %in% known) {
    cli::cli_abort(
      c(
        "Invalid {.arg how} value {.val {how}}.",
        i = "Choose one of {.val {known}}."
      ),
      class = "biogate_error_invalid_mode"
    )
  }
}

#' Check biological identifiers
#'
#' Validate a vector of identifiers against a source. `pattern` mode checks that
#' each identifier is well-formed. `cache` mode also checks that it exists in a
#' pinned local snapshot (see [biogate_snapshots()]). `remote` mode checks live
#' existence against the source API. `existence` mode uses a snapshot when one is
#' available for `version` and otherwise falls back to `remote`.
#'
#' @param x A vector of identifiers. Coerced to character.
#' @param source_db Source key, for example `"mondo"`. See [sources()].
#' @param how Checking mode: `"pattern"` (offline, shape only), `"cache"`
#'   (offline existence against a snapshot), `"remote"` (live existence against
#'   the source API), or `"existence"` (cache when a snapshot is available for
#'   `version`, otherwise remote).
#' @param species Optional species context, echoed in the result. A name such as
#'   `"homo_sapiens"` or an NCBI taxon id such as `9606`. When given, an id of a
#'   different species is invalid: Ensembl is checked from its id prefix (in
#'   `pattern` and `remote` modes), and UniProt from the entry's organism in
#'   `remote` mode. A species outside the source map is not checked.
#' @param version Snapshot version. Required for `cache` mode; selects the
#'   snapshot for `existence` mode; ignored in `pattern` and `remote` modes.
#' @return A [tibble][tibble::tibble] with one row per element of `x` and the
#'   columns `input`, `valid`, `normalized`, `suggestion`, `source_db`,
#'   `version`, `species`, and `how`.
#' @seealso [is_valid_id()], [sources()], [source_info()], [biogate_snapshots()].
#' @examples
#' check_id(c("MONDO:0005148", "mondo:5148"), source_db = "mondo")
#' check_id("MONDO:0005148", source_db = "mondo", how = "cache", version = "sample")
#' @export
check_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL
) {
  .assert_check_args(x, source_db, how, species, version)
  .assert_mode_supported(how)
  source <- .get_source(source_db)

  x <- as.character(x)
  n <- length(x)
  is_na <- is.na(x)

  if (identical(how, "cache")) {
    if (is.null(version)) {
      installed <- .snapshot_versions(source_db)
      cli::cli_abort(
        c(
          "{.arg version} is required for {.val cache} mode.",
          i = "Installed versions for {.val {source_db}}: {.val {installed}}."
        ),
        class = "biogate_error_missing_version"
      )
    }
    version <- as.character(version)
    verdicts <- .cache_verdicts(
      source,
      x,
      is_na,
      .snapshot_set(source_db, version)
    )
    version_col <- version
  } else if (identical(how, "remote")) {
    verdicts <- .remote_verdicts(source, x, is_na, species)
    version_col <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  } else if (identical(how, "existence")) {
    # Cache-then-remote fallback: answer from a pinned snapshot when one is
    # available for the requested version, otherwise check live.
    snap_version <- if (is.null(version)) {
      NA_character_
    } else {
      as.character(version)
    }
    snap_path <- if (is.na(snap_version)) {
      NA_character_
    } else {
      .snapshot_file(source_db, snap_version)
    }
    if (!is.na(snap_path)) {
      verdicts <- .cache_verdicts(
        source,
        x,
        is_na,
        .snapshot_set(source_db, snap_version)
      )
      version_col <- snap_version
    } else {
      verdicts <- .remote_verdicts(source, x, is_na, species)
      version_col <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
    }
  } else {
    verdicts <- .pattern_verdicts(source, x, is_na, species)
    version_col <- NA_character_
  }

  species_val <- if (is.null(species)) NA_character_ else as.character(species)
  tibble::tibble(
    input = x,
    valid = verdicts$valid,
    normalized = verdicts$normalized,
    suggestion = verdicts$suggestion,
    source_db = rep(source_db, n),
    version = rep(version_col, n),
    species = rep(species_val, n),
    how = rep(how, n)
  )
}

#' Test biological identifiers
#'
#' A convenience wrapper over [check_id()] that returns only the verdict.
#'
#' @inheritParams check_id
#' @return A logical vector, one element per element of `x`.
#' @seealso [check_id()].
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
