# Offline species-gating tests for remote mode. The biogate.remote_transport
# option replaces the network seam so no request ever leaves the machine.

# Ensembl answers 200 for a known id and 400 for a well-formed but unknown one.
.stub_ensembl_species <- function(present_ids) {
  function(url, timeout) {
    id <- sub(".*lookup/id/([^?]+).*", "\\1", url)
    if (id %in% present_ids) {
      list(status = 200, body = NULL)
    } else {
      list(status = 400, body = NULL)
    }
  }
}

# UniProt maps each known accession to a body carrying its organism taxon id.
.stub_uniprot_species <- function(bodies) {
  function(url, timeout) {
    acc <- sub(".*uniprotkb/([^.?/]+).*", "\\1", url)
    if (acc %in% names(bodies)) {
      list(status = 200, body = bodies[[acc]])
    } else {
      list(status = 404, body = NULL)
    }
  }
}

.human_body <- list(
  entryType = "UniProtKB reviewed (Swiss-Prot)",
  organism = list(taxonId = 9606)
)

.mouse_body <- list(
  entryType = "UniProtKB reviewed (Swiss-Prot)",
  organism = list(taxonId = 10090)
)

test_that("an ensembl id is gated by its encoded species", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_ensembl_species("ENSMUSG00000059552")
  )

  match <- check_id(
    "ENSMUSG00000059552",
    source_db = "ensembl",
    how = "remote",
    species = "mus_musculus"
  )
  expect_true(match$valid)
  expect_identical(match$normalized, "ENSMUSG00000059552")

  mismatch <- check_id(
    "ENSMUSG00000059552",
    source_db = "ensembl",
    how = "remote",
    species = "homo_sapiens"
  )
  expect_false(mismatch$valid)
  expect_true(is.na(mismatch$normalized))
})

test_that("a uniprot accession is gated by the entry's organism taxon", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_uniprot_species(list(P01308 = .human_body))
  )

  expect_true(
    check_id(
      "P01308",
      source_db = "uniprot",
      how = "remote",
      species = "homo_sapiens"
    )$valid
  )
  expect_true(
    check_id(
      "P01308",
      source_db = "uniprot",
      how = "remote",
      species = 9606
    )$valid
  )
  expect_false(
    check_id(
      "P01308",
      source_db = "uniprot",
      how = "remote",
      species = "mus_musculus"
    )$valid
  )
})

test_that("a species outside the source map is not checked", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_uniprot_species(list(P01308 = .human_body))
  )

  res <- check_id(
    "P01308",
    source_db = "uniprot",
    how = "remote",
    species = "drosophila_melanogaster"
  )
  expect_true(res$valid)
})

test_that("a uniprot species verdict round-trips through the cache", {
  withr::local_envvar(BIOGATE_CACHE_DIR = withr::local_tempdir())
  withr::local_options(
    biogate.remote_transport = .stub_uniprot_species(list(P04925 = .mouse_body))
  )

  # The first lookup populates the cache with the organism taxon.
  expect_true(
    check_id(
      "P04925",
      source_db = "uniprot",
      how = "remote",
      species = "mus_musculus"
    )$valid
  )

  # A forbidding transport proves the species verdict reads from the cache.
  withr::local_options(
    biogate.remote_transport = function(url, timeout) {
      stop("network must not be used when a cached response exists")
    }
  )
  expect_true(
    check_id(
      "P04925",
      source_db = "uniprot",
      how = "remote",
      species = "mus_musculus"
    )$valid
  )
  expect_false(
    check_id(
      "P04925",
      source_db = "uniprot",
      how = "remote",
      species = "homo_sapiens"
    )$valid
  )
})
