# biogate (development version)

* `hgnc` now reports `cache` mode. It has always shipped an approved-symbol
  snapshot that cache mode can use, but it did not advertise the mode, so
  `source_info()` hid it. `biogate_pull()` still refuses `hgnc`, since there is no
  download builder for it.
* `check_id()` and `is_valid_id()` gain a `refresh` argument for `remote` and
  `existence` checks. When `TRUE`, a cached response is ignored and the id is
  looked up live again.
* Remote checks now record when each response was retrieved. A cached verdict
  reports its original fetch time in the `version` column instead of the time of
  the current run. Set the `BIOGATE_REMOTE_TTL` environment variable to a number
  of seconds to refetch a cached response once it is older than that.
* Snapshot and remote-cache files are written atomically, so an interrupted write
  can no longer leave a truncated file that reports valid ids as invalid.
* Remote checks retry a transient network failure or a 429 or 5xx response a few
  times with exponential backoff before giving up, so a brief blip no longer
  fails a whole batch.
* The NCBI E-utilities checks (`refseq`, `clinvar`) send an API key when the
  `NCBI_API_KEY` environment variable is set, which raises NCBI's rate limit from
  three to ten requests a second. `NCBI_EMAIL` is included when set.
* `ncbitaxon` is a new source for NCBI Taxonomy identifiers such as
  `NCBITaxon:9606`. It checks the pattern offline and existence against NCBI
  Taxonomy in the Ontology Lookup Service, reusing the OLS resolver. A bare taxon
  number or a different-case prefix is suggested in canonical CURIE form. No cache
  builder is offered, since the NCBI Taxonomy OBO release is far too large to
  snapshot.
* `inchikey` is a new source for InChIKey chemical structure keys such as
  `BSYNRYMUTXBXSQ-UHFFFAOYSA-N`. This is pattern mode only; a lowercase input is
  suggested in its canonical uppercase form. An existence check would need a
  UniChem or PubChem lookup, which is not offered yet.
* `ncit` is a new source for NCI Thesaurus concept codes such as `NCIT:C3224`,
  and `eco` for Evidence and Conclusion Ontology terms such as `ECO:0000269`.
  Both check the pattern offline and existence against their ontology in the
  Ontology Lookup Service, reusing the OLS resolver.
* Five InterPro member databases are new sources: `smart` (`SM00248`), `panther`
  (`PTHR11003`), `cdd` (`cd00029`), `prints` (`PR00001`), and `ncbifam`
  (`TIGR00001` or `NF000001`). Each checks the pattern offline and existence
  against the EBI InterPro API, reusing the interpro resolver.
* `mirbase_hairpin` is a new source for miRBase hairpin precursor accessions such
  as `MI0000001`, a sibling to the mature `mirbase` source. It checks the pattern
  offline and existence against RNAcentral through EBI Search, reusing the mirbase
  resolver.
* `mirbase` gains `remote` mode. A mature accession is checked for existence
  against RNAcentral through EBI Search, which indexes miRBase. miRBase has no
  existence API of its own. This is an existence check only; a withdrawn
  accession is reported as absent, not with a successor.
* `prosite` gains `remote` mode. A pattern or profile accession is checked for
  existence against the ExPASy PROSITE entry endpoint, which resolves both entry
  types from one address. This is an existence check only; a deleted accession is
  reported as absent, not with a successor.
* `orphanet` gains `remote` mode. A rare-disease id is checked against the
  Orphanet Rare Disease Ontology in the Ontology Lookup Service, reusing the OLS
  resolver. The `ORPHA` prefix is rewritten to the ontology's `Orphanet` prefix
  for the lookup, and an obsolete term is reported with its successor.
* `clinvar` gains `remote` mode. An accession is checked for existence by
  searching ClinVar through NCBI E-utilities. One search covers all three
  accession types (VCV, RCV, and SCV). This is an existence check only.
* `refseq` gains `remote` mode. An accession is checked for existence against
  NCBI E-utilities, routed to the nucleotide or protein database by its molecule
  prefix. The summary endpoint returns an empty result for an unknown accession.
  This is an existence check only; a suppressed accession is not distinguished
  from a current one.
* `rfam`, `uniparc`, `complexportal`, and `wikipathways` gain `remote` mode. Each
  checks existence against its source: the Rfam API, the UniProt UniParc
  endpoint, the EBI Complex Portal web service, and the published WikiPathways
  asset. All four are existence checks; an absent id is reported as not valid
  with no successor.
* `interpro` and `pfam` gain `remote` mode. An accession is checked for existence
  against the EBI InterPro API, which hosts both databases, so one resolver
  serves the two sources. The entry endpoint answers 204 for a well-formed
  accession that is not a current entry. This is an existence check only; a
  deleted accession is reported as absent, not with a successor.
* `chembl` gains `remote` mode. A ChEMBL id is checked for existence against the
  ChEMBL id-lookup endpoint, which resolves an id of any entity type, so one
  lookup covers compounds, targets, assays, and documents alike. This is an
  existence check only; an obsolete id is not yet reported with a successor.
* `reactome` gains `remote` mode. A stable id is checked for existence against
  the Reactome content service. This is an existence check only; a superseded
  stable id is not yet reported with its successor.
* `pdb` gains `remote` mode. A four-character structure id is checked for
  existence against the RCSB PDB data API. This is an existence check only; an
  obsoleted structure that was superseded is not yet reported with its
  successor.
* The Python package installs a `biogate` command-line tool. It validates
  identifiers from arguments, a file, or standard input, prints per-id results
  as text, TSV, or JSON, and exits non-zero when any input is invalid, so it
  drops into shell pipelines and CI. It also has `biogate sources` and
  `biogate info`.
* The Python package adds a Great Expectations column-map expectation,
  `biogate.gx.ExpectColumnValuesToBeValidId`, for validating a data frame
  column. Install it with `pip install "biogate[gx]"`.
* `id_predicate()` now documents its use as a pointblank `col_vals_expr()` step,
  alongside assertr and validate. The predicate is unchanged; pointblank
  consumes it directly.

# biogate 0.1.0

* First numbered release. Sets the version to 0.1.0 in both the R and Python
  packages so they track together.
* `source_info()` gains an `example` identifier and a `modes` column for each
  source, so it now answers "what does a valid id look like and how can I check
  it?". The Python package gains a matching `source_info()`.
* Adds a documentation website. The R reference and the getting-started vignette
  are built with pkgdown, the Python guide and API reference with MkDocs, and a
  shared landing page links the two. A `docs` workflow builds both on every pull
  request and publishes them to GitHub Pages from `main`.
* Adds the OBO ontology sources `pato`, `mp`, and `bto` for qualities
  (`PATO:0000001`), mammalian phenotypes (`MP:0001262`), and tissues
  (`BTO:0000759`), each with `pattern` and live OLS `remote` modes.
* Adds the OBO ontology sources `so`, `hp`, `doid`, `uberon`, and `cl` for
  sequence features (`SO:0000704`), phenotypes (`HP:0001250`), diseases
  (`DOID:9352`), anatomy (`UBERON:0002107`), and cell types (`CL:0000236`). Each
  supports `pattern` mode with prefix and zero-pad suggestions and live `remote`
  existence through the Ontology Lookup Service.
* Adds `uniparc`, `complexportal`, `cosmic`, and `pharmgkb` `pattern` sources for
  unique protein sequences (`UPI0000000001`), macromolecular complexes
  (`CPX-2158`), somatic mutations (`COSM476`), and PharmGKB accessions (`PA267`).
  Each suggests the canonical uppercase for a lowercase input.
* Adds `wikipathways`, `orphanet`, and `mirbase` `pattern` sources for pathways
  (`WP554`), rare diseases (`ORPHA:558`), and mature microRNAs (`MIMAT0000001`).
  Each suggests the canonical uppercase for a lowercase input.
* Adds `drugbank`, `clinvar`, and `ec` `pattern` sources for drug accessions
  (`DB00001`), ClinVar records (`VCV000012345`), and Enzyme Commission numbers
  (`1.1.1.1`). The first two suggest the canonical uppercase for a lowercase
  input.
* Adds `pfam`, `rfam`, and `prosite` `pattern` sources for protein families
  (`PF00001`), RNA families (`RF00001`), and PROSITE patterns and profiles
  (`PS00001`). Each suggests the canonical uppercase for a lowercase input.
* Adds `reactome` and `interpro` `pattern` sources. `reactome` checks Reactome
  stable ids such as `R-HSA-68886`, and `interpro` checks InterPro ids such as
  `IPR000001`. Both suggest the canonical uppercase for a lowercase input.
* Adds two more `pattern` sources. `chembl` checks ChEMBL identifiers such as
  `CHEMBL25`, and `pdb` checks Protein Data Bank structure ids such as `4HHB`.
  Both suggest the canonical uppercase for a lowercase input.
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
