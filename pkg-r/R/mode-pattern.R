# Pattern mode: offline, deterministic checks against a source regex.
# Full-string PCRE anchors (\A ... \z) match Python's re.fullmatch element for
# element, given ASCII character classes in the shared patterns.

.full_pattern <- function(pattern) {
  paste0("\\A(?:", pattern, ")\\z")
}

.matches <- function(pattern, x) {
  grepl(.full_pattern(pattern), x, perl = TRUE)
}

.zero_pad <- function(local, width) {
  if (nchar(local) >= width) {
    return(local)
  }
  paste0(strrep("0", width - nchar(local)), local)
}

.suggest_one <- function(source, s) {
  if (is.na(s)) {
    return(NA_character_)
  }
  curie <- source$curie
  if (!is.null(curie)) {
    prefix <- curie$prefix
    pad_to <- curie$pad_to
    idx <- regexpr(":", s, fixed = TRUE)
    if (idx > 0L) {
      head <- substr(s, 1L, idx - 1L)
      local <- substr(s, idx + 1L, nchar(s))
    } else {
      head <- prefix
      local <- s
    }
    if (toupper(head) != toupper(prefix)) {
      return(NA_character_)
    }
    if (!is.null(pad_to) && grepl("^[0-9]+$", local)) {
      local <- .zero_pad(local, pad_to)
    }
    candidate <- paste0(prefix, ":", local)
    if (!identical(candidate, s) && .matches(source$pattern, candidate)) {
      return(candidate)
    }
    return(NA_character_)
  }
  norm <- source$normalize
  if (
    !is.null(norm) && !is.null(norm$case) && norm$case %in% c("upper", "lower")
  ) {
    candidate <- if (identical(norm$case, "upper")) toupper(s) else tolower(s)
    if (!identical(candidate, s) && .matches(source$pattern, candidate)) {
      return(candidate)
    }
  }
  NA_character_
}

# Species code between ENS and the feature letter for an Ensembl stable id, or
# NA when the string is not an Ensembl stable id. Human ids yield "".
.ensembl_id_prefix <- function(id) {
  m <- regmatches(id, regexec("^ENS([A-Z]*)[EFGPT][0-9]{11}$", id))[[1]]
  if (length(m) == 2L) m[2L] else NA_character_
}

# Expected species prefix for the requested species, or NULL when the species
# is not in the map. Matches by name or by NCBI taxon id. The taxon branch only
# fires for a numeric species, mirroring Python's `entry["taxon"] == species`
# where an int never equals a string: a string like "9606" is not treated as a
# taxon here (only a name), so R and Python agree.
.ensembl_species_prefix <- function(species_block, species) {
  for (entry in species_block$map) {
    if (
      identical(as.character(entry$name), as.character(species)) ||
        (is.numeric(species) && isTRUE(entry$taxon == species))
    ) {
      return(entry$prefix)
    }
  }
  NULL
}

# TRUE unless the source is species-aware, the id is an Ensembl stable id, the
# requested species is in the map, and the id's species code does not match.
.species_ok <- function(source, id, species) {
  if (is.null(species) || is.na(id)) {
    return(TRUE)
  }
  # Use [[ ]] to avoid partial matching against a "species_aware" key.
  species_block <- source[["species"]]
  if (
    is.null(species_block) ||
      !identical(species_block$scheme, "ensembl_prefix")
  ) {
    return(TRUE)
  }
  expected <- .ensembl_species_prefix(species_block, species)
  if (is.null(expected)) {
    return(TRUE)
  }
  id_prefix <- .ensembl_id_prefix(id)
  if (is.na(id_prefix)) {
    return(TRUE)
  }
  identical(id_prefix, expected)
}

# Shape-only verdicts: valid when the string is well-formed for the source. When
# a species is given, a well-formed id whose species does not match is invalid.
.pattern_verdicts <- function(source, x, is_na, species = NULL) {
  n <- length(x)
  base_match <- rep(NA, n)
  base_match[!is_na] <- .matches(source$pattern, x[!is_na])
  species_ok <- rep(TRUE, n)
  if (!is.null(species)) {
    for (i in which(!is_na)) {
      species_ok[i] <- .species_ok(source, x[i], species)
    }
  }
  valid <- base_match & species_ok
  normalized <- ifelse(!is_na & valid, x, NA_character_)
  suggestion <- rep(NA_character_, n)
  for (i in which(!is_na & !base_match)) {
    candidate <- .suggest_one(source, x[i])
    if (!is.na(candidate) && .species_ok(source, candidate, species)) {
      suggestion[i] <- candidate
    }
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}
