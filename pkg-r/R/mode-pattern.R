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

# Shape-only verdicts: valid when the string is well-formed for the source.
.pattern_verdicts <- function(source, x, is_na) {
  n <- length(x)
  valid <- rep(NA, n)
  valid[!is_na] <- .matches(source$pattern, x[!is_na])
  normalized <- ifelse(!is_na & valid, x, NA_character_)
  suggestion <- rep(NA_character_, n)
  for (i in which(!is_na & !valid)) {
    suggestion[i] <- .suggest_one(source, x[i])
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}
