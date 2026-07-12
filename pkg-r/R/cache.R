# Cache mode: offline existence checks against a pinned snapshot of valid ids.

.read_ids <- function(path) {
  ids <- trimws(readLines(path, warn = FALSE, encoding = "UTF-8"))
  ids[nzchar(ids)]
}

# Write lines to a path atomically: write a temporary file in the same directory,
# then rename it over the target in one step. A crash or a concurrent reader never
# sees a half-written file, so a truncated snapshot or cache cannot silently
# report valid ids as invalid. On Windows a rename cannot overwrite an existing
# file, so fall back to an overwriting copy there.
.atomic_write_lines <- function(lines, path) {
  tmp <- paste0(path, ".", Sys.getpid(), ".tmp")
  writeLines(lines, tmp)
  if (!isTRUE(file.rename(tmp, path))) {
    file.copy(tmp, path, overwrite = TRUE)
    unlink(tmp)
  }
  invisible(path)
}

.bundled_snapshots_dir <- function() {
  system.file("extdata", "snapshots", package = "biogate")
}

.snapshot_file <- function(source_db, version) {
  user <- file.path(biogate_cache_dir(), source_db, paste0(version, ".txt"))
  if (file.exists(user)) {
    return(user)
  }
  bundled_root <- .bundled_snapshots_dir()
  if (nzchar(bundled_root)) {
    bundled <- file.path(bundled_root, source_db, paste0(version, ".txt"))
    if (file.exists(bundled)) {
      return(bundled)
    }
  }
  NA_character_
}

.retired_file <- function(source_db, version) {
  user <- file.path(
    biogate_cache_dir(),
    source_db,
    paste0(version, ".retired.tsv")
  )
  if (file.exists(user)) {
    return(user)
  }
  bundled_root <- .bundled_snapshots_dir()
  if (nzchar(bundled_root)) {
    bundled <- file.path(
      bundled_root,
      source_db,
      paste0(version, ".retired.tsv")
    )
    if (file.exists(bundled)) {
      return(bundled)
    }
  }
  NA_character_
}

.snapshot_versions <- function(source_db) {
  dirs <- c(
    file.path(biogate_cache_dir(), source_db),
    if (nzchar(.bundled_snapshots_dir())) {
      file.path(.bundled_snapshots_dir(), source_db)
    }
  )
  versions <- character(0)
  for (d in dirs) {
    if (dir.exists(d)) {
      versions <- c(
        versions,
        sub("\\.txt$", "", list.files(d, pattern = "\\.txt$"))
      )
    }
  }
  sort(unique(versions))
}

.snapshot_set <- function(source_db, version) {
  path <- .snapshot_file(source_db, version)
  if (is.na(path)) {
    available <- .snapshot_versions(source_db)
    cli::cli_abort(
      c(
        "No snapshot for {.val {source_db}} version {.val {version}}.",
        i = if (length(available)) {
          "Installed versions: {.val {available}}."
        } else {
          "No snapshots are installed for this source."
        },
        i = "Run {.code biogate_pull()} to download one."
      ),
      class = "biogate_error_missing_snapshot"
    )
  }
  .read_ids(path)
}

# Retired-id map for a snapshot version, read from the "<version>.retired.tsv"
# sidecar. Each non-blank line is "retired<TAB>successor"; the successor is the
# second tab field, or "" when absent. Returns a named character vector mapping
# retired id to successor, empty when the source has no sidecar.
.snapshot_retired <- function(source_db, version) {
  path <- .retired_file(source_db, version)
  empty <- character(0)
  names(empty) <- character(0)
  if (is.na(path)) {
    return(empty)
  }
  lines <- trimws(readLines(path, warn = FALSE, encoding = "UTF-8"))
  lines <- lines[nzchar(lines)]
  if (!length(lines)) {
    return(empty)
  }
  keys <- character(length(lines))
  successors <- character(length(lines))
  for (i in seq_along(lines)) {
    fields <- strsplit(lines[i], "\t", fixed = TRUE)[[1]]
    keys[i] <- fields[1]
    successors[i] <- if (length(fields) >= 2L) fields[2] else ""
  }
  names(successors) <- keys
  successors
}

.cache_verdicts <- function(source, x, is_na, ids, retired = character(0)) {
  n <- length(x)
  valid <- rep(NA, n)
  normalized <- rep(NA_character_, n)
  suggestion <- rep(NA_character_, n)
  wellformed <- rep(NA, n)
  wellformed[!is_na] <- .matches(source$pattern, x[!is_na])
  for (i in seq_len(n)) {
    if (is_na[i]) {
      next
    }
    if (isTRUE(wellformed[i])) {
      if (x[i] %in% ids) {
        valid[i] <- TRUE
        normalized[i] <- x[i]
      } else {
        valid[i] <- FALSE
        if (x[i] %in% names(retired)) {
          succ <- retired[[x[i]]]
          if (nzchar(succ)) {
            suggestion[i] <- succ
          }
        }
      }
    } else {
      valid[i] <- FALSE
      sugg <- .suggest_one(source, x[i])
      if (!is.na(sugg) && sugg %in% ids) {
        suggestion[i] <- sugg
      }
    }
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}

#' Snapshot cache directory
#'
#' The directory where downloaded snapshots are stored. Set the environment
#' variable `BIOGATE_CACHE_DIR` to override the default.
#'
#' @return A path to the cache directory.
#' @examples
#' biogate_cache_dir()
#' @export
biogate_cache_dir <- function() {
  override <- Sys.getenv("BIOGATE_CACHE_DIR", unset = "")
  if (nzchar(override)) {
    return(override)
  }
  tools::R_user_dir("biogate", which = "cache")
}

#' List installed snapshots
#'
#' Reports snapshots available for `cache` mode, both downloaded ones in the
#' cache directory and the small bundled samples.
#'
#' @return A [tibble][tibble::tibble] with columns `source`, `version`,
#'   `n_ids`, and `location` (`"cache"` or `"bundled"`).
#' @examples
#' biogate_snapshots()
#' @export
biogate_snapshots <- function() {
  locations <- list(
    cache = biogate_cache_dir(),
    bundled = .bundled_snapshots_dir()
  )
  rows <- list()
  for (loc in names(locations)) {
    base <- locations[[loc]]
    if (!nzchar(base) || !dir.exists(base)) {
      next
    }
    files <- list.files(
      base,
      pattern = "\\.txt$",
      recursive = TRUE,
      full.names = TRUE
    )
    for (path in files) {
      rows[[length(rows) + 1L]] <- data.frame(
        source = basename(dirname(path)),
        version = sub("\\.txt$", "", basename(path)),
        n_ids = length(.read_ids(path)),
        location = loc,
        stringsAsFactors = FALSE
      )
    }
  }
  if (!length(rows)) {
    return(tibble::tibble(
      source = character(0),
      version = character(0),
      n_ids = integer(0),
      location = character(0)
    ))
  }
  tibble::as_tibble(do.call(rbind, rows))
}

.sanitize_version <- function(raw) {
  raw <- sub("^releases/", "", trimws(raw))
  gsub("[^A-Za-z0-9._-]", "-", raw)
}

# Extract (version, ids) from OBO lines, keeping ids that match the pattern.
.parse_obo <- function(lines, pattern) {
  version <- NA_character_
  dv <- grep("^data-version:", lines, value = TRUE)
  if (length(dv)) {
    version <- .sanitize_version(sub("^data-version:", "", dv[1]))
  }
  id_values <- sub("^id:\\s*", "", grep("^id:\\s", lines, value = TRUE))
  ids <- sort(unique(id_values[.matches(pattern, id_values)]))
  list(
    version = if (is.na(version) || !nzchar(version)) NULL else version,
    ids = ids
  )
}

#' Download a snapshot for cache mode
#'
#' Fetches the source's OBO release, keeps the identifiers that match the source
#' pattern, and writes them to the cache directory as a snapshot. The version
#' defaults to the ontology's own data-version.
#'
#' @param source_db Source key, for example `"mondo"`.
#' @param version Snapshot version label. Defaults to the ontology data-version.
#' @param quiet Suppress progress messages.
#' @return The path to the written snapshot, invisibly.
#' @seealso [biogate_snapshots()], [check_id()].
#' @export
biogate_pull <- function(source_db, version = NULL, quiet = FALSE) {
  source <- .get_source(source_db)
  cache <- source$cache
  if (is.null(cache) || !identical(cache$builder, "obo")) {
    cli::cli_abort(
      "No snapshot builder is available for {.val {source_db}}.",
      class = "biogate_error_no_builder"
    )
  }
  tmp <- tempfile(fileext = ".obo")
  on.exit(unlink(tmp), add = TRUE)
  if (!quiet) {
    cli::cli_inform("Downloading {.url {cache$obo_url}} ...")
  }
  utils::download.file(
    cache$obo_url,
    tmp,
    quiet = quiet,
    mode = "wb",
    headers = c(
      "User-Agent" = "biogate/0.1 (+https://github.com/samuelbharti/biogate)"
    )
  )
  parsed <- .parse_obo(
    readLines(tmp, warn = FALSE, encoding = "UTF-8"),
    source$pattern
  )
  version <- if (is.null(version)) parsed$version else as.character(version)
  if (is.null(version) || !nzchar(version)) {
    cli::cli_abort(
      "Could not determine a version for {.val {source_db}}; pass {.arg version}.",
      class = "biogate_error_missing_version"
    )
  }
  dest_dir <- file.path(biogate_cache_dir(), source_db)
  dir.create(dest_dir, recursive = TRUE, showWarnings = FALSE)
  dest <- file.path(dest_dir, paste0(version, ".txt"))
  .atomic_write_lines(parsed$ids, dest)
  if (!quiet) {
    cli::cli_inform("Wrote {length(parsed$ids)} ids to {.file {dest}}.")
  }
  invisible(dest)
}
