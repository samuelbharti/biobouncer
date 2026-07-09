# biogate 0.0.0.9000

* `remote` mode is species-aware. An id that exists but belongs to a different
  species than requested is invalid: Ensembl is checked from its id prefix and
  UniProt from the entry's organism taxon id.
* `pattern` mode is species-aware for Ensembl. When `species` is given, a
  well-formed id whose encoded species does not match is invalid, and a
  malformed id is only suggested when the correction matches the species. A
  species outside the source map is not checked.
* `check_id()` gains `existence` mode: it answers from a pinned snapshot when one
  is available for the requested `version` and otherwise falls back to `remote`.
* `check_id()` gains live `remote` mode: existence checks against a source API.
  The Ontology Lookup Service resolver covers mondo, efo, go, and chebi.
  Responses are cached on disk, and a network failure raises an error rather
  than returning a silent `FALSE`.
* `remote` mode adds Ensembl and UniProt resolvers, so `ensembl` and `uniprot`
  ids can be checked live. A retired (deleted) UniProt accession is reported as
  not valid.
* `check_id()` gains offline `cache` mode: existence checks against a pinned
  snapshot. A small `sample` snapshot for the ontology sources ships with the
  package, and `biogate_cache_dir()` and `biogate_snapshots()` manage snapshots.
* `biogate_pull()` downloads a full snapshot from a source's OBO release into the
  cache directory (mondo, efo, go, chebi).
* `check_id()` and `is_valid_id()` implement offline `pattern` mode for an
  initial set of sources (mondo, efo, go, chebi, ensembl, uniprot).
* `sources()` and `source_info()` list what can be checked.
* Arguments are validated with checkmate, errors are raised with cli and carry a
  condition class, and `check_id()` returns a tibble.
* Initial package scaffold.
