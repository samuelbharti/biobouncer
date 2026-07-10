# biogate 0.0.0.9000

* `dbsnp` gains `remote` mode. An rsID is checked for existence against the NCBI
  dbSNP RefSNP API. An rsID that was merged into another still resolves but is
  not current, so it is not valid and suggests the primary id.
* Adds two `pattern` sources. `refseq` checks NCBI RefSeq accessions such as
  `NM_000546.6`, with an optional version, and suggests the canonical uppercase
  for a lowercase input. `dbsnp` checks dbSNP reference SNP ids such as `rs7412`,
  and suggests lowercase for an uppercase prefix.
* `hgvs` gains `remote` mode. A variant is checked against the Mutalyzer
  normalizer, which confirms the reference sequence exists and the change is
  consistent with it, such as the stated reference base and coordinates in
  range. This goes beyond the offline syntax check. Only inputs that pass the
  offline grammar are looked up, and the response is cached on disk.
* Adds an `hgvs` source that checks the syntax of HGVS sequence variant names,
  for example `NM_004006.2:c.4375C>T` or `NP_003997.1:p.(Gly56Ala)`. This is a
  grammar check in `pattern` mode: it covers substitutions, deletions,
  duplications, insertions, deletion-insertions, inversions, and the common
  protein forms including frameshifts, across the g, o, m, c, n, r, and p
  coordinate types. It checks syntax only. It does not check coordinate order or
  that a variant exists, and it requires a reference sequence.
* Adds validation-framework adapters that wrap the core classifier:
  `assert_valid_id()`, `check_valid_id()`, and `test_valid_id()` in the checkmate
  style, `sv_biogate()`, a shinyvalidate rule, and `id_predicate()`, an
  elementwise predicate for data-frame validation with assertr or validate. The
  Python package pairs these with a pandera check.
* Adds an `hgnc` source for HUGO gene symbols. `cache` mode checks a symbol
  against the approved-symbol snapshot, and a withdrawn or previous symbol
  resolves to its approved successor through the retired-map (for example `MLL`
  suggests `KMT2A`). Symbols are case-sensitive.
* Retired identifiers are detected with a successor suggestion. In `remote` mode
  an OLS term that exists but is obsolete is invalid and suggests its
  `replaced_by` successor. In `cache` mode a snapshot can carry a
  `<version>.retired.tsv` sidecar; an id retired in that version is invalid and
  suggests its successor. A cross-ontology successor is suggested as-is.
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
