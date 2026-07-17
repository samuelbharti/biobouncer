# Fuzzy "did you mean" suggestions by bounded edit distance. Used only in cache
# and existence modes, where a local set of valid ids is available. Specified to
# match _fuzzy.py exactly: Levenshtein with unit costs, the nearest candidate
# within the configured distance, ties broken by the code-point-smallest.

# The nearest id to s within the source's fuzzy edit distance, or NA. Only a
# candidate whose length is within the distance can match, so the search is
# limited to those. adist() computes the same unit-cost Levenshtein as the Python
# side, and radix order breaks ties by code point.
#
# When the source sets suggest.case_insensitive, distance is measured between
# lowercase forms so a difference in case costs no edits, matching the
# ignore_case branch of fuzzy_suggest(). The candidates keep their original
# spelling throughout, so the returned suggestion and the code-point tie-break
# are both on the snapshot's own spelling, exactly as in Python.
.fuzzy_suggest <- function(source, s, ids) {
  cfg <- source[["suggest"]]$fuzzy
  if (is.null(cfg)) {
    return(NA_character_)
  }
  k <- suppressWarnings(as.integer(cfg$max_distance))
  if (is.na(k) || length(ids) == 0L) {
    return(NA_character_)
  }
  cand <- ids[abs(nchar(ids) - nchar(s)) <= k]
  if (!length(cand)) {
    return(NA_character_)
  }
  ignore_case <- isTRUE(source[["suggest"]]$case_insensitive)
  probe <- if (ignore_case) tolower(s) else s
  target <- if (ignore_case) tolower(cand) else cand
  d <- as.integer(adist(probe, target))
  keep <- !is.na(d) & d <= k
  if (!any(keep)) {
    return(NA_character_)
  }
  cand <- cand[keep]
  d <- d[keep]
  best <- cand[d == min(d)]
  sort(best, method = "radix")[1]
}
