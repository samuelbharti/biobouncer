# Remote mode: live existence checks against a source API.
# Mirrors cache mode, with "membership in a snapshot set" replaced by
# "exists via the resolver". Results carry a UTC retrieval timestamp.

.remote_user_agent <- function() {
  "biogate/0.1 (+https://github.com/samuelbharti/biogate)"
}

# Parse a JSON body, tolerating an empty or non-json payload. A proxy or outage
# can return html instead of json; that is not an error to raise here, since the
# status decides the verdict, so an unparseable body becomes NULL.
.remote_parse_body <- function(txt) {
  if (!nzchar(txt)) {
    return(NULL)
  }
  tryCatch(
    jsonlite::fromJSON(txt, simplifyVector = FALSE),
    error = function(e) NULL
  )
}

# Single network seam. Tests replace it with the biogate.remote_transport option.
.remote_http_get <- function(url, timeout = 30) {
  transport <- getOption("biogate.remote_transport", NULL)
  if (is.function(transport)) {
    return(transport(url, timeout))
  }
  handle <- curl::new_handle(
    useragent = .remote_user_agent(),
    timeout = timeout
  )
  resp <- tryCatch(
    curl::curl_fetch_memory(url, handle = handle),
    error = function(e) {
      cli::cli_abort(
        c(
          "Remote request failed for {.url {url}}.",
          i = conditionMessage(e)
        ),
        class = "biogate_error_remote"
      )
    }
  )
  list(
    status = resp$status_code,
    body = .remote_parse_body(rawToChar(resp$content))
  )
}

.remote_cache_path <- function(onto, id) {
  file.path(
    biogate_cache_dir(),
    "remote",
    "ols",
    onto,
    paste0(gsub(":", "_", id), ".json")
  )
}

.ols_url <- function(onto, id) {
  sprintf(
    "https://www.ebi.ac.uk/ols4/api/ontologies/%s/terms?obo_id=%s",
    onto,
    id
  )
}

# Matching-term count in an OLS response, 0 when absent or malformed.
.ols_count <- function(body) {
  total <- tryCatch(
    as.integer(body$page$totalElements),
    error = function(e) NA_integer_
  )
  if (length(total) == 0L || is.na(total)) {
    0L
  } else {
    total
  }
}

# On-disk response cache. Only 200 and 404 responses are cached, and a corrupt
# cache file is ignored and refetched.
.ols_request <- function(onto, id, refresh = FALSE) {
  path <- .remote_cache_path(onto, id)
  if (!refresh && file.exists(path)) {
    cached <- tryCatch(
      jsonlite::fromJSON(path, simplifyVector = FALSE),
      error = function(e) NULL
    )
    if (!is.null(cached)) {
      return(list(status = cached$status, body = cached$body))
    }
  }
  url <- .ols_url(onto, id)
  resp <- .remote_http_get(url)
  if (resp$status == 200 || resp$status == 404) {
    stored <- if (resp$status == 200) {
      list(page = list(totalElements = .ols_count(resp$body)))
    } else {
      NULL
    }
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    writeLines(
      jsonlite::toJSON(
        list(status = resp$status, body = stored, url = url),
        auto_unbox = TRUE,
        null = "null"
      ),
      path
    )
  }
  resp
}

.ols_exists <- function(onto, id) {
  resp <- .ols_request(onto, id)
  if (resp$status == 200) {
    return(isTRUE(.ols_count(resp$body) >= 1L))
  }
  if (resp$status == 404) {
    return(FALSE)
  }
  cli::cli_abort(
    c(
      "Unexpected remote status {.val {resp$status}} for {.val {id}}.",
      i = "Existence could not be determined."
    ),
    class = "biogate_error_remote"
  )
}

# Resolvers map a source and a set of ids to a named logical existence vector.
.remote_resolvers <- list(
  ols = function(source, ids) {
    onto <- source$remote$ols_ontology
    vapply(
      ids,
      function(id) .ols_exists(onto, id),
      logical(1),
      USE.NAMES = TRUE
    )
  }
)

.get_resolver <- function(source) {
  remote <- source$remote
  if (
    is.null(remote) ||
      is.null(remote$resolver) ||
      !remote$resolver %in% names(.remote_resolvers)
  ) {
    cli::cli_abort(
      c(
        "No remote resolver for {.val {source$key}}.",
        i = "Remote mode needs a source with a supported resolver."
      ),
      class = "biogate_error_no_resolver"
    )
  }
  .remote_resolvers[[remote$resolver]]
}

# Live existence verdicts. Mirrors .cache_verdicts, batching lookups into one
# resolver call over the unique ids that need checking.
.remote_verdicts <- function(source, x, is_na) {
  resolver <- .get_resolver(source)
  n <- length(x)
  valid <- rep(NA, n)
  normalized <- rep(NA_character_, n)
  suggestion <- rep(NA_character_, n)
  wellformed <- rep(NA, n)
  wellformed[!is_na] <- .matches(source$pattern, x[!is_na])

  candidate <- rep(NA_character_, n)
  for (i in which(!is_na & !wellformed)) {
    candidate[i] <- .suggest_one(source, x[i])
  }

  need <- unique(c(
    x[which(!is_na & wellformed)],
    candidate[!is.na(candidate)]
  ))
  exists_map <- if (length(need)) {
    resolver(source, need)
  } else {
    logical(0)
  }

  for (i in seq_len(n)) {
    if (is_na[i]) {
      next
    }
    if (isTRUE(wellformed[i])) {
      if (isTRUE(exists_map[[x[i]]])) {
        valid[i] <- TRUE
        normalized[i] <- x[i]
      } else {
        valid[i] <- FALSE
      }
    } else {
      valid[i] <- FALSE
      cand <- candidate[i]
      if (!is.na(cand) && isTRUE(exists_map[[cand]])) {
        suggestion[i] <- cand
      }
    }
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}
