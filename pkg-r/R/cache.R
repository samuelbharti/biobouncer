# Cache mode: offline existence checks against a pinned snapshot of valid ids.

.read_ids <- function(path) {
  ids <- trimws(readLines(path, warn = FALSE, encoding = "UTF-8"))
  ids[nzchar(ids)]
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

.cache_verdicts <- function(source, x, is_na, ids) {
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
