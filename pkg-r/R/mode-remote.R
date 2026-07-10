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

# Turn an identifier into a safe file name: every character outside
# [A-Za-z0-9._-] becomes "_". Keeps an id with a colon, a slash, or a ">" (such
# as an HGVS variant) usable as a cache or fixture file name. Matches the rule
# in _remote.py.
.safe_ident <- function(id) {
  gsub("[^A-Za-z0-9._-]", "_", id)
}

# Cache path for a resolved id, keyed by resolver and its subdirectory.
.remote_cache_path <- function(resolver, subkey, id) {
  file.path(
    biogate_cache_dir(),
    "remote",
    resolver,
    subkey,
    paste0(.safe_ident(id), ".json")
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

# Normalize an OBO reference to a colon obo_id. Accepts a short form such as
# "GO_0006915", a full IRI such as ".../MONDO_0005016", or NULL/empty. Takes the
# substring after the last slash, then turns the first underscore into a colon.
# Returns NULL for a NULL or empty input.
.normalize_obo <- function(s) {
  if (is.null(s) || length(s) != 1L || !nzchar(s)) {
    return(NULL)
  }
  tail <- sub(".*/", "", s)
  sub("_", ":", tail)
}

# Whether a UniProtKB entry is active. A retired accession returns 200 with an
# "Inactive" entryType, which is not valid. A NULL, missing, or non-character
# entryType is treated as inactive.
.uniprot_active <- function(body) {
  entry <- body$entryType
  if (!is.character(entry) || length(entry) != 1L) {
    return(FALSE)
  }
  startsWith(entry, "UniProtKB")
}

# Raise for a status that cannot decide existence. Fetches never cache such a
# response, so a later run retries it.
.remote_abort_status <- function(status) {
  cli::cli_abort(
    c(
      "Unexpected remote status {.val {status}}.",
      i = "Existence could not be determined."
    ),
    class = "biogate_error_remote"
  )
}

# Taxon id for the requested species. Matches a map entry by name, otherwise
# accepts a bare taxon number, otherwise NULL for a species outside the map.
.species_taxon <- function(species_block, species) {
  for (entry in species_block$map) {
    if (identical(as.character(entry$name), as.character(species))) {
      return(entry$taxon)
    }
  }
  if (grepl("^[0-9]+$", as.character(species))) {
    return(as.integer(species))
  }
  NULL
}

# TRUE unless the source is species-aware for UniProt, the requested species is
# known, the entry's organism taxon is known, and the two do not match. Lenient
# when any of those inputs is missing.
.uniprot_species_ok <- function(source, body, species) {
  if (is.null(species)) {
    return(TRUE)
  }
  # Use [[ ]] to avoid partial matching against a "species_aware" key.
  block <- source[["species"]]
  if (is.null(block) || !identical(block$scheme, "uniprot_organism")) {
    return(TRUE)
  }
  taxon <- .species_taxon(block, species)
  if (is.null(taxon) || is.null(body$organism$taxonId)) {
    return(TRUE)
  }
  isTRUE(as.integer(body$organism$taxonId) == as.integer(taxon))
}

# The primary rsID number a merged RefSNP record points to, or NULL for a
# primary record.
.dbsnp_merged_into <- function(body) {
  merged <- tryCatch(
    body$merged_snapshot_data$merged_into,
    error = function(e) NULL
  )
  if (is.null(merged) || length(merged) == 0L) {
    return(NULL)
  }
  as.character(merged[[1]])
}

# Shared building blocks for existence-only resolvers whose whole verdict is the
# HTTP status: 200 exists, 404 is absent, the body is never consulted, and the id
# is neither species scoped nor tracked for retirement.
.exists_by_404 <- function(status, body) {
  if (status == 200) {
    return(TRUE)
  }
  if (status == 404) {
    return(FALSE)
  }
  .remote_abort_status(status)
}
.no_cache_body <- function(status, body) NULL
.species_agnostic <- function(source, id, body, species) TRUE
.never_retired <- function(source, body) list(retired = FALSE, successor = NULL)

# RefSeq accessions split across two NCBI databases by their molecule prefix.
# Protein accessions live in the protein database; the rest are nucleotide
# records in nuccore.
.refseq_protein_prefixes <- c("AP", "NP", "WP", "XP", "YP", "ZP")
.refseq_db <- function(id) {
  prefix <- toupper(sub("_.*$", "", id))
  if (prefix %in% .refseq_protein_prefixes) "protein" else "nuccore"
}
# Whether an E-utilities esummary response resolved the accession to a uid.
.esummary_has_uid <- function(body) {
  uids <- tryCatch(body$result$uids, error = function(e) NULL)
  length(uids) >= 1L
}
# The hit count from an E-utilities esearch response (it is a string).
.esearch_count <- function(body) {
  count <- tryCatch(body$esearchresult$count, error = function(e) NULL)
  if (is.null(count) || length(count) == 0L) {
    return(0L)
  }
  n <- suppressWarnings(as.integer(count))
  if (is.na(n)) 0L else n
}

# Resolver definitions. Each maps a source and id to a URL, decides existence
# from a status and body, and names the minimal body to persist. A resolver is
# selected by source$remote$resolver and names its cache and fixture subtree.
.remote_resolvers <- list(
  ols = list(
    name = "ols",
    subkey = function(source) source$remote$ols_ontology,
    url = function(source, id) {
      # A source may set obo_prefix to rewrite the id's prefix for OLS, for
      # example ORPHA:558 becomes Orphanet:558 for the ordo ontology.
      obo <- if (!is.null(source$remote$obo_prefix)) {
        paste0(source$remote$obo_prefix, ":", sub("^[^:]*:", "", id))
      } else {
        id
      }
      sprintf(
        "https://www.ebi.ac.uk/ols4/api/ontologies/%s/terms?obo_id=%s",
        source$remote$ols_ontology,
        obo
      )
    },
    exists = function(status, body) {
      if (status == 200) {
        return(isTRUE(.ols_count(body) >= 1L))
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    cache_body = function(status, body) {
      if (status == 200) {
        term <- tryCatch(
          body$"_embedded"$terms[[1]],
          error = function(e) NULL
        )
        list(
          page = list(totalElements = .ols_count(body)),
          "_embedded" = list(
            terms = list(list(
              is_obsolete = isTRUE(term$is_obsolete),
              term_replaced_by = term$term_replaced_by
            ))
          )
        )
      } else {
        NULL
      }
    },
    species_ok = function(source, id, body, species) TRUE,
    retired = function(source, body) {
      term <- tryCatch(
        body$"_embedded"$terms[[1]],
        error = function(e) NULL
      )
      if (isTRUE(term$is_obsolete)) {
        list(
          retired = TRUE,
          successor = .normalize_obo(term$term_replaced_by)
        )
      } else {
        list(retired = FALSE, successor = NULL)
      }
    }
  ),
  ensembl = list(
    name = "ensembl",
    subkey = function(source) "id",
    url = function(source, id) {
      sprintf(
        "https://rest.ensembl.org/lookup/id/%s?content-type=application/json",
        id
      )
    },
    # Ensembl answers 400 for a well-formed but unknown id; a 404 is treated as
    # absent too.
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 400 || status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    cache_body = function(status, body) NULL,
    species_ok = function(source, id, body, species) {
      .species_ok(source, id, species)
    },
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  uniprot = list(
    name = "uniprot",
    subkey = function(source) "uniprotkb",
    url = function(source, id) {
      sprintf("https://rest.uniprot.org/uniprotkb/%s.json", id)
    },
    exists = function(status, body) {
      if (status == 200) {
        return(.uniprot_active(body))
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    cache_body = function(status, body) {
      if (status == 200) {
        taxon <- tryCatch(body$organism$taxonId, error = function(e) NULL)
        list(
          entryType = body$entryType,
          organism = list(taxonId = taxon)
        )
      } else {
        NULL
      }
    },
    species_ok = function(source, id, body, species) {
      .uniprot_species_ok(source, body, species)
    },
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  mutalyzer = list(
    name = "mutalyzer",
    subkey = function(source) "normalize",
    url = function(source, id) {
      paste0(
        "https://mutalyzer.nl/api/normalize/",
        utils::URLencode(id, reserved = TRUE)
      )
    },
    # Mutalyzer normalizes a valid variant (200) and rejects one that is not
    # consistent with its reference (422): a wrong reference base, a coordinate
    # out of range, or a reference that does not exist.
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 422) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # The status carries the whole verdict, so no body is worth persisting.
    cache_body = function(status, body) NULL,
    # An HGVS variant is named against a specific reference, not a species map.
    species_ok = function(source, id, body, species) TRUE,
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  dbsnp = list(
    name = "dbsnp",
    subkey = function(source) "refsnp",
    url = function(source, id) {
      number <- if (startsWith(tolower(id), "rs")) substring(id, 3) else id
      paste0("https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/", number)
    },
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # Persist only the merge pointer; a primary record needs no body.
    cache_body = function(status, body) {
      if (status == 200) {
        target <- .dbsnp_merged_into(body)
        if (!is.null(target)) {
          return(list(
            merged_snapshot_data = list(merged_into = list(target))
          ))
        }
      }
      NULL
    },
    species_ok = function(source, id, body, species) TRUE,
    # A merged rsID still resolves but is not current; suggest the primary id.
    retired = function(source, body) {
      target <- .dbsnp_merged_into(body)
      if (!is.null(target)) {
        list(retired = TRUE, successor = paste0("rs", target))
      } else {
        list(retired = FALSE, successor = NULL)
      }
    }
  ),
  pdb = list(
    name = "pdb",
    subkey = function(source) "entry",
    url = function(source, id) {
      paste0("https://data.rcsb.org/rest/v1/core/entry/", id)
    },
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # The status carries the whole verdict, so no body is worth persisting.
    cache_body = function(status, body) NULL,
    # A structure is not species scoped for this existence check.
    species_ok = function(source, id, body, species) TRUE,
    # Existence only; an obsoleted-with-successor entry is not modeled yet.
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  chembl = list(
    name = "chembl",
    subkey = function(source) "lookup",
    # The id-lookup endpoint resolves a ChEMBL id of any entity type (compound,
    # target, assay, document, and so on), so one call covers the whole source.
    url = function(source, id) {
      paste0(
        "https://www.ebi.ac.uk/chembl/api/data/chembl_id_lookup/",
        id,
        ".json"
      )
    },
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # The status carries the whole verdict, so no body is worth persisting.
    cache_body = function(status, body) NULL,
    # A ChEMBL id is not species scoped for this existence check.
    species_ok = function(source, id, body, species) TRUE,
    # Existence only; the lookup status field is not interpreted yet, so an
    # obsolete id is not reported with a successor.
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  reactome = list(
    name = "reactome",
    subkey = function(source) "query",
    url = function(source, id) {
      paste0("https://reactome.org/ContentService/data/query/", id)
    },
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # The status carries the whole verdict, so no body is worth persisting.
    cache_body = function(status, body) NULL,
    # The species is encoded in the stable id prefix, not checked against a map.
    species_ok = function(source, id, body, species) TRUE,
    # Existence only; a superseded stable id is not reported with a successor yet.
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  interpro = list(
    name = "interpro",
    subkey = function(source) source$remote$interpro_db,
    # One InterPro API serves several member databases; the source names which
    # (interpro or pfam), and the entry path selects it.
    url = function(source, id) {
      paste0(
        "https://www.ebi.ac.uk/interpro/api/entry/",
        source$remote$interpro_db,
        "/",
        id
      )
    },
    # The entry endpoint answers 204 (no content) for a well-formed accession
    # that is not a current entry, and 200 when it exists.
    exists = function(status, body) {
      if (status == 200) {
        return(TRUE)
      }
      if (status == 204 || status == 404) {
        return(FALSE)
      }
      .remote_abort_status(status)
    },
    # The status carries the whole verdict, so no body is worth persisting.
    cache_body = function(status, body) NULL,
    # A family or domain accession is not species scoped.
    species_ok = function(source, id, body, species) TRUE,
    # Existence only; a deleted accession is reported as absent, not with a
    # successor.
    retired = function(source, body) list(retired = FALSE, successor = NULL)
  ),
  rfam = list(
    name = "rfam",
    subkey = function(source) "family",
    url = function(source, id) {
      paste0("https://rfam.org/family/", id, "?content-type=application/json")
    },
    exists = .exists_by_404,
    cache_body = .no_cache_body,
    species_ok = .species_agnostic,
    retired = .never_retired
  ),
  uniparc = list(
    name = "uniparc",
    subkey = function(source) "uniparc",
    url = function(source, id) {
      paste0("https://rest.uniprot.org/uniparc/", id, ".json")
    },
    exists = .exists_by_404,
    cache_body = .no_cache_body,
    species_ok = .species_agnostic,
    retired = .never_retired
  ),
  complexportal = list(
    name = "complexportal",
    subkey = function(source) "complex",
    url = function(source, id) {
      paste0("https://www.ebi.ac.uk/intact/complex-ws/complex/", id)
    },
    exists = .exists_by_404,
    cache_body = .no_cache_body,
    species_ok = .species_agnostic,
    retired = .never_retired
  ),
  wikipathways = list(
    name = "wikipathways",
    subkey = function(source) "pathways",
    # The asset path repeats the id: .../pathways/WP554/WP554.gpml.
    url = function(source, id) {
      paste0(
        "https://www.wikipathways.org/wikipathways-assets/pathways/",
        id,
        "/",
        id,
        ".gpml"
      )
    },
    exists = .exists_by_404,
    cache_body = .no_cache_body,
    species_ok = .species_agnostic,
    retired = .never_retired
  ),
  refseq = list(
    name = "refseq",
    subkey = function(source) "esummary",
    url = function(source, id) {
      paste0(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=",
        .refseq_db(id),
        "&id=",
        id,
        "&retmode=json"
      )
    },
    # esummary answers 200 with an empty uid list and an error field for an
    # unknown accession, so existence is decided from the body, not the status.
    exists = function(status, body) {
      if (status != 200) {
        .remote_abort_status(status)
      }
      .esummary_has_uid(body)
    },
    # Persist only the resolved uid list, which is all existence needs.
    cache_body = function(status, body) {
      if (status == 200) {
        uids <- tryCatch(body$result$uids, error = function(e) NULL)
        if (is.null(uids)) {
          uids <- list()
        }
        list(result = list(uids = as.list(uids)))
      } else {
        NULL
      }
    },
    species_ok = .species_agnostic,
    retired = .never_retired
  ),
  clinvar = list(
    name = "clinvar",
    subkey = function(source) "esearch",
    # esearch matches a full accession of any type (VCV, RCV, or SCV), so one
    # search covers the whole source.
    url = function(source, id) {
      paste0(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "?db=clinvar&term=",
        id,
        "&retmode=json"
      )
    },
    exists = function(status, body) {
      if (status != 200) {
        .remote_abort_status(status)
      }
      .esearch_count(body) >= 1L
    },
    # Persist only the hit count, which is all existence needs.
    cache_body = function(status, body) {
      if (status == 200) {
        list(esearchresult = list(count = as.character(.esearch_count(body))))
      } else {
        NULL
      }
    },
    species_ok = .species_agnostic,
    retired = .never_retired
  )
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

# Resolve one id, reading an on-disk cached response when present and definitive.
# exists() raises for an indeterminate status, so it runs before the cache write
# and such a response is never cached. A corrupt cache file is ignored and
# refetched. The cache is keyed only by id; species is compared at read time
# against the cached body, so a mismatch is a FALSE verdict, not a miss.
.remote_lookup <- function(
  resolver,
  source,
  id,
  species = NULL,
  refresh = FALSE
) {
  path <- .remote_cache_path(resolver$name, resolver$subkey(source), id)
  resp <- NULL
  if (!refresh && file.exists(path)) {
    cached <- tryCatch(
      jsonlite::fromJSON(path, simplifyVector = FALSE),
      error = function(e) NULL
    )
    if (!is.null(cached) && !is.null(cached$status)) {
      resp <- list(status = cached$status, body = cached$body)
    }
  }
  if (is.null(resp)) {
    url <- resolver$url(source, id)
    resp <- .remote_http_get(url)
    exists <- resolver$exists(resp$status, resp$body)
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    writeLines(
      jsonlite::toJSON(
        list(
          status = resp$status,
          body = resolver$cache_body(resp$status, resp$body),
          url = url
        ),
        auto_unbox = TRUE,
        null = "null"
      ),
      path
    )
  } else {
    exists <- resolver$exists(resp$status, resp$body)
  }
  if (!isTRUE(exists)) {
    return(list(valid = FALSE, suggestion = NULL))
  }
  if (!isTRUE(resolver$species_ok(source, id, resp$body, species))) {
    return(list(valid = FALSE, suggestion = NULL))
  }
  ret <- resolver$retired(source, resp$body)
  if (isTRUE(ret$retired)) {
    return(list(valid = FALSE, suggestion = ret$successor))
  }
  list(valid = TRUE, suggestion = NULL)
}

# Batch a resolver over a set of ids, returning a named list of the per-id
# list(valid, suggestion) results. valid is TRUE only when the id exists and
# matches the requested species; suggestion carries an obsolete term's successor.
.resolve_ids <- function(resolver, source, ids, species) {
  results <- lapply(
    ids,
    function(id) .remote_lookup(resolver, source, id, species)
  )
  names(results) <- ids
  results
}

# Live existence verdicts. Mirrors .cache_verdicts, batching lookups into one
# resolver pass over the unique ids that need checking. When a species is given,
# a map value is TRUE only when the id exists and matches that species.
.remote_verdicts <- function(source, x, is_na, species = NULL) {
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
  results <- if (length(need)) {
    .resolve_ids(resolver, source, need, species)
  } else {
    list()
  }

  for (i in seq_len(n)) {
    if (is_na[i]) {
      next
    }
    if (isTRUE(wellformed[i])) {
      res <- results[[x[i]]]
      if (isTRUE(res$valid)) {
        valid[i] <- TRUE
        normalized[i] <- x[i]
      } else {
        valid[i] <- FALSE
        if (!is.null(res$suggestion)) {
          suggestion[i] <- res$suggestion
        }
      }
    } else {
      valid[i] <- FALSE
      cand <- candidate[i]
      if (!is.na(cand) && isTRUE(results[[cand]]$valid)) {
        suggestion[i] <- cand
      }
    }
  }
  list(valid = valid, normalized = normalized, suggestion = suggestion)
}
