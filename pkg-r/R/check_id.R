.assert_check_args <- function(x, source_db, how, species, version, refresh) {
  checkmate::assert_atomic(x, .var.name = "x")
  checkmate::assert_string(source_db, .var.name = "source_db")
  checkmate::assert_string(how, .var.name = "how")
  checkmate::assert_flag(refresh, .var.name = "refresh")
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
#' available for `version`, otherwise falls back to `remote`, and for a source
#' with no resolver falls back to `pattern`.
#'
#' @param x A vector of identifiers. Coerced to character.
#' @param source_db Source key, for example `"mondo"`. See [sources()].
#' @param how Checking mode: `"pattern"` (offline, shape only), `"cache"`
#'   (offline existence against a snapshot), `"remote"` (live existence against
#'   the source API), or `"existence"` (cache when a snapshot is available for
#'   `version`, otherwise remote, or pattern for a source with no resolver).
#' @param species Optional species context, echoed in the result. A name such as
#'   `"homo_sapiens"` or an NCBI taxon id such as `9606`. When given, an id of a
#'   different species is invalid: Ensembl is checked from its id prefix (in
#'   `pattern` and `remote` modes), and UniProt from the entry's organism in
#'   `remote` mode. A species outside the source map is not checked.
#' @param version Snapshot version. In `cache` mode it selects the snapshot and
#'   defaults to the latest installed one when omitted; it selects the snapshot
#'   for `existence` mode; ignored in `pattern` and `remote` modes.
#' @param refresh In remote checks, skip any cached response and refetch. Ignored
#'   by the offline modes.
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
  version = NULL,
  refresh = FALSE
) {
  .assert_check_args(x, source_db, how, species, version, refresh)
  .assert_mode_supported(how)
  source <- .get_source(source_db)

  x <- as.character(x)
  n <- length(x)
  is_na <- is.na(x)

  if (identical(how, "cache")) {
    if (is.null(version)) {
      # Default to the latest installed snapshot rather than forcing the caller
      # to name a version. Only abort when nothing is installed.
      version <- .default_cache_version(source_db, source)
      if (is.null(version)) {
        cli::cli_abort(
          c(
            "No snapshot is installed for {.val {source_db}} to default to.",
            i = "Pass a {.arg version} or run {.code biogate_pull({source_db})}."
          ),
          class = "biogate_error_missing_version"
        )
      }
    } else {
      version <- as.character(version)
    }
    verdicts <- .cache_verdicts(
      source,
      x,
      is_na,
      .snapshot_set(source_db, version),
      .snapshot_retired(source_db, version)
    )
    version_col <- rep(version, n)
  } else if (identical(how, "remote")) {
    verdicts <- .remote_verdicts(source, x, is_na, species, refresh)
    call_stamp <- .utc_stamp()
    version_col <- ifelse(is.na(verdicts$version), call_stamp, verdicts$version)
  } else if (identical(how, "existence")) {
    # Cache-then-remote-then-pattern fallback: answer from a pinned snapshot when
    # one is available for the requested version, else check live, else (for a
    # source with no resolver) degrade to a shape check rather than aborting.
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
        .snapshot_set(source_db, snap_version),
        .snapshot_retired(source_db, snap_version)
      )
      version_col <- rep(snap_version, n)
    } else if (!is.null(source$remote)) {
      verdicts <- .remote_verdicts(source, x, is_na, species, refresh)
      call_stamp <- .utc_stamp()
      version_col <- ifelse(
        is.na(verdicts$version),
        call_stamp,
        verdicts$version
      )
    } else {
      verdicts <- .pattern_verdicts(source, x, is_na, species)
      version_col <- rep(NA_character_, n)
    }
  } else {
    verdicts <- .pattern_verdicts(source, x, is_na, species)
    version_col <- rep(NA_character_, n)
  }

  species_val <- if (is.null(species)) NA_character_ else as.character(species)
  tibble::tibble(
    input = x,
    valid = verdicts$valid,
    normalized = verdicts$normalized,
    suggestion = verdicts$suggestion,
    source_db = rep(source_db, n),
    version = version_col,
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
  version = NULL,
  refresh = FALSE
) {
  check_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version,
    refresh = refresh
  )$valid
}
