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
  system.file("extdata", "snapshots", package = "biobouncer")
}

# Locate a snapshot file, plain or gzipped, user cache before bundled. suffix is
# ".txt" for the id set or ".retired.tsv" for the retired map. readLines() reads a
# .gz path transparently, so only the lookup needs to know about compression.
.find_snapshot <- function(source_db, version, suffix) {
  roots <- c(biobouncer_cache_dir(), .bundled_snapshots_dir())
  for (root in roots) {
    if (!nzchar(root)) {
      next
    }
    for (ext in c(suffix, paste0(suffix, ".gz"))) {
      path <- file.path(root, source_db, paste0(version, ext))
      if (file.exists(path)) {
        return(path)
      }
    }
  }
  NA_character_
}

.snapshot_file <- function(source_db, version) {
  .find_snapshot(source_db, version, ".txt")
}

.retired_file <- function(source_db, version) {
  .find_snapshot(source_db, version, ".retired.tsv")
}

.snapshot_versions <- function(source_db) {
  dirs <- c(
    file.path(biobouncer_cache_dir(), source_db),
    if (nzchar(.bundled_snapshots_dir())) {
      file.path(.bundled_snapshots_dir(), source_db)
    }
  )
  versions <- character(0)
  for (d in dirs) {
    if (dir.exists(d)) {
      versions <- c(
        versions,
        sub("\\.txt(\\.gz)?$", "", list.files(d, pattern = "\\.txt(\\.gz)?$"))
      )
    }
  }
  sort(unique(versions))
}

# The snapshot version cache mode uses when the caller gives none. Prefers the
# source's pinned default_version when a snapshot for it is installed, then the
# newest installed non-sample version, then a bundled sample. Returns NULL when
# nothing is installed. Newest is by sort order, which is chronological for the
# dated (ISO-8601) versions snapshots use. Mirrors default_cache_version() in the
# Python package.
.default_cache_version <- function(source_db, source) {
  installed <- .snapshot_versions(source_db)
  if (!length(installed)) {
    return(NULL)
  }
  dv <- source$default_version
  if (!is.null(dv) && dv %in% installed) {
    return(dv)
  }
  non_sample <- installed[installed != "sample"]
  if (length(non_sample)) {
    return(non_sample[length(non_sample)])
  }
  installed[length(installed)]
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
        i = "Run {.code biobouncer_pull()} to download one."
      ),
      class = "biobouncer_error_missing_snapshot"
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
    if (isFALSE(valid[i]) && is.na(suggestion[i])) {
      fz <- .fuzzy_suggest(source, x[i], ids)
      if (!is.na(fz)) {
        suggestion[i] <- fz
      }
    }
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}

#' Snapshot cache directory
#'
#' The directory where downloaded snapshots are stored. Set the environment
#' variable `BIOBOUNCER_CACHE_DIR` to override the default.
#'
#' @return A path to the cache directory.
#' @examples
#' biobouncer_cache_dir()
#' @export
biobouncer_cache_dir <- function() {
  override <- Sys.getenv("BIOBOUNCER_CACHE_DIR", unset = "")
  if (nzchar(override)) {
    return(override)
  }
  tools::R_user_dir("biobouncer", which = "cache")
}

#' List installed snapshots
#'
#' Reports snapshots available for `cache` mode, both downloaded ones in the
#' cache directory and the small bundled samples.
#'
#' @return A [tibble][tibble::tibble] with columns `source`, `version`,
#'   `n_ids`, and `location` (`"cache"` or `"bundled"`).
#' @examples
#' biobouncer_snapshots()
#' @export
biobouncer_snapshots <- function() {
  locations <- list(
    cache = biobouncer_cache_dir(),
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
      pattern = "\\.txt(\\.gz)?$",
      recursive = TRUE,
      full.names = TRUE
    )
    for (path in files) {
      rows[[length(rows) + 1L]] <- data.frame(
        source = basename(dirname(path)),
        version = sub("\\.txt(\\.gz)?$", "", basename(path)),
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
  ids <- sort(unique(id_values[.matches(pattern, id_values)]), method = "radix")
  list(
    version = if (is.na(version) || !nzchar(version)) NULL else version,
    ids = ids
  )
}

# Empty retired map: a named character vector with no entries.
.empty_retired <- function() {
  out <- character(0)
  names(out) <- character(0)
  out
}

# Split an HGNC multi-value field on "|", trimming surrounding quotes and spaces.
.split_pipe <- function(field) {
  field <- gsub('^"|"$', "", trimws(field))
  if (!nzchar(field)) {
    return(character(0))
  }
  toks <- gsub('^"|"$', "", trimws(strsplit(field, "|", fixed = TRUE)[[1]]))
  toks[nzchar(toks)]
}

# Extract (version, approved ids, retired map) from an HGNC complete-set TSV.
# Mirrors parse_hgnc_tsv() in the Python package exactly: the approved set is
# every "symbol" with status "Approved" that matches the pattern; the retired
# map sends a previous or alias symbol to its approved successor, a previous
# symbol wins over an alias, an approved symbol is never retired, and an
# ambiguous mapping is dropped. Everything is sorted by code point (radix) so
# the two languages write byte-identical snapshots.
.parse_hgnc_tsv <- function(lines, pattern) {
  if (!length(lines)) {
    return(list(version = NULL, ids = character(0), retired = .empty_retired()))
  }
  header <- strsplit(lines[1], "\t", fixed = TRUE)[[1]]
  c_symbol <- match("symbol", header)
  c_status <- match("status", header)
  if (is.na(c_symbol) || is.na(c_status)) {
    cli::cli_abort(
      "HGNC TSV is missing the {.field symbol} or {.field status} column."
    )
  }
  c_prev <- match("prev_symbol", header)
  c_alias <- match("alias_symbol", header)

  data <- lines[-1]
  data <- data[nzchar(trimws(data))]
  fields_list <- strsplit(data, "\t", fixed = TRUE)
  col <- function(i) {
    vapply(
      fields_list,
      function(f) if (length(f) >= i) f[i] else NA_character_,
      character(1)
    )
  }
  symbol <- trimws(col(c_symbol))
  status <- trimws(col(c_status))
  ok <- !is.na(symbol) & nzchar(symbol) & !is.na(status) & status == "Approved"
  ok[ok] <- .matches(pattern, symbol[ok])
  approved <- sort(unique(symbol[ok]), method = "radix")

  prev_map <- list()
  alias_map <- list()
  for (j in which(ok)) {
    sym <- symbol[j]
    fields <- fields_list[[j]]
    if (!is.na(c_prev) && length(fields) >= c_prev) {
      for (old in .split_pipe(fields[c_prev])) {
        prev_map[[old]] <- unique(c(prev_map[[old]], sym))
      }
    }
    if (!is.na(c_alias) && length(fields) >= c_alias) {
      for (old in .split_pipe(fields[c_alias])) {
        alias_map[[old]] <- unique(c(alias_map[[old]], sym))
      }
    }
  }

  keys <- sort(unique(c(names(prev_map), names(alias_map))), method = "radix")
  keys <- keys[nzchar(keys) & !(keys %in% approved)]
  if (length(keys)) {
    keys <- keys[.matches(pattern, keys)]
  }
  retired_keys <- character(0)
  retired_vals <- character(0)
  for (old in keys) {
    targets <- if (!is.null(prev_map[[old]])) {
      prev_map[[old]]
    } else {
      alias_map[[old]]
    }
    if (length(targets) == 1L) {
      retired_keys <- c(retired_keys, old)
      retired_vals <- c(retired_vals, targets)
    }
  }
  names(retired_vals) <- retired_keys
  list(version = NULL, ids = approved, retired = retired_vals)
}

# Snapshot builders, keyed by the source's cache$builder. Each has
# url(source, version) and build(lines, source) -> list(version, ids, retired).
# Mirrors the Python _BUILDERS registry.
.builders <- list(
  obo = list(
    url = function(source, version) source$cache$obo_url,
    build = function(lines, source) {
      parsed <- .parse_obo(lines, source$pattern)
      list(
        version = parsed$version,
        ids = parsed$ids,
        retired = .empty_retired()
      )
    }
  ),
  hgnc_tsv = list(
    url = function(source, version) {
      template <- source$cache$tsv_url
      resolved <- if (!is.null(version)) version else source$default_version
      if (grepl("{version}", template, fixed = TRUE)) {
        gsub("{version}", resolved, template, fixed = TRUE)
      } else {
        template
      }
    },
    build = function(lines, source) .parse_hgnc_tsv(lines, source$pattern)
  )
)

#' Download a snapshot for cache mode
#'
#' Dispatches on the source's `cache$builder`: `obo` fetches the ontology
#' release, `hgnc_tsv` fetches the HGNC complete set. Identifiers that match the
#' source pattern are written to the cache directory as a snapshot, and a
#' retired-id map, when the builder produces one, to the matching
#' `<version>.retired.tsv` sidecar. An OBO version defaults to the ontology's own
#' data-version; an HGNC version defaults to the source's `default_version`.
#'
#' @param source_db Source key, for example `"mondo"`.
#' @param version Snapshot version label. Defaults to the builder's own version.
#' @param quiet Suppress progress messages.
#' @return The path to the written snapshot, invisibly.
#' @seealso [biobouncer_snapshots()], [check_id()].
#' @export
biobouncer_pull <- function(source_db, version = NULL, quiet = FALSE) {
  source <- .get_source(source_db)
  cache <- source$cache
  builder <- if (is.null(cache) || is.null(cache$builder)) {
    NULL
  } else {
    .builders[[cache$builder]]
  }
  if (is.null(builder)) {
    cli::cli_abort(
      "No snapshot builder is available for {.val {source_db}}.",
      class = "biobouncer_error_no_builder"
    )
  }
  url <- builder$url(source, version)
  tmp <- tempfile()
  on.exit(unlink(tmp), add = TRUE)
  if (!quiet) {
    cli::cli_inform("Downloading {.url {url}} ...")
  }
  utils::download.file(
    url,
    tmp,
    quiet = quiet,
    mode = "wb",
    headers = c(
      "User-Agent" = "biobouncer/0.1 (+https://github.com/samuelbharti/biobouncer)"
    )
  )
  built <- builder$build(
    readLines(tmp, warn = FALSE, encoding = "UTF-8"),
    source
  )
  version <- if (!is.null(version)) {
    as.character(version)
  } else if (!is.null(built$version)) {
    built$version
  } else {
    source$default_version
  }
  if (is.null(version) || !nzchar(version)) {
    cli::cli_abort(
      "Could not determine a version for {.val {source_db}}; pass {.arg version}.",
      class = "biobouncer_error_missing_version"
    )
  }
  dest_dir <- file.path(biobouncer_cache_dir(), source_db)
  dir.create(dest_dir, recursive = TRUE, showWarnings = FALSE)
  dest <- file.path(dest_dir, paste0(version, ".txt"))
  .atomic_write_lines(built$ids, dest)
  retired <- built$retired
  if (length(retired)) {
    keys <- sort(names(retired), method = "radix")
    .atomic_write_lines(
      paste(keys, retired[keys], sep = "\t"),
      file.path(dest_dir, paste0(version, ".retired.tsv"))
    )
  }
  if (!quiet) {
    cli::cli_inform("Wrote {length(built$ids)} ids to {.file {dest}}.")
  }
  invisible(dest)
}
