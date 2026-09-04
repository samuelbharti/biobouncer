# Changelog

All notable changes to the Python package are recorded here. The R package keeps
a matching changelog in `pkg-r/NEWS.md`; the two packages share one version.

## 0.2.0

### Changed

- Posit Software, PBC is added as a copyright holder in the LICENSE file.

### Notes

- A JavaScript package joins the R and Python packages in the same repository,
  with the same verdicts for the same input.
- 0.1.4 was released on CRAN only. This is the first PyPI release since 0.1.3,
  and it includes the 0.1.4 changes listed below.

### Fixed

- A gnomAD id with a `chr` prefix now gets a suggestion when an allele or the
  chromosome is lowercase, so `chr1-55516888-g-a` suggests `chr1-55516888-G-A`.
  An uppercase `CHR` prefix is suggested as `chr`. No verdict changes (#89).

## 0.1.4

### Added

- Two pattern sources for model-organism identifiers. `mgi` validates an MGI
  accession, such as `MGI:97306`, and `rgd` validates an RGD identifier, such
  as `RGD:3059`. Both require the prefix, since the bare number the registries
  record would accept any digits, and both repair a bare id or a lowercase
  prefix to the canonical form.

- Two pattern sources for genomic variant coordinates. `gnomad` validates a
  gnomAD-style `chrom-pos-ref-alt` string, such as `1-55516888-G-A`, with an
  optional `chr` prefix. `spdi` validates NCBI SPDI notation, such as
  `NC_000001.11:55516887:G:A`. Both check the coordinate shape offline in
  `pattern` mode, so an empty allele or a malformed field is rejected rather than
  passed through as valid.

### Notes

- The release is timed by the R package, which is answering CRAN feedback on its
  first submission with documentation-only changes. The two packages share one
  version.

## 0.1.3

No functional change to the Python package. Released to keep the version aligned
with the R package's first CRAN submission.

## 0.1.2

### Fixed

- A lowercase gene symbol now suggests the right gene. `hgnc` suggestions in
  `cache` and `existence` mode ignore case, so `tp53` suggests `TP53` and `brca1`
  suggests `BRCA1`. Case previously spent the edit budget, which left a symbol
  either with no suggestion (`brca1` is four edits from `BRCA1`) or with the wrong
  one (`tp53` is two edits from both `TP53` and `CD53`, and the tie-break chose
  `CD53`). A lowercase typo resolves too: `tp52` suggests `TP53` rather than
  `CD52`.

  A case-wrong symbol stays invalid and carries the approved spelling as a
  suggestion, so `report()` and `repair()` clean it while an adapter still flags
  the cell. Suggestions use the snapshot's own spelling, so `C9ORF72` and
  `c9orf72` both suggest `C9orf72` rather than an uppercased form.

## 0.1.1

First release published to PyPI. `pip install biobouncer` now works. There is no
behavior change from 0.1.0 and the source list is unchanged.

### Fixed

- The source distribution no longer ships the built documentation site, the docs
  sources, or the example and theme directories. The sdist had no explicit file
  list, so those were picked up from the working tree; it drops from 1.6 MB to
  517 KB. The wheel was never affected.

### Notes

- A release now publishes to PyPI automatically, authenticated with Trusted
  Publishing rather than a stored API token. Before uploading, the release checks
  that the R and Python versions agree with the tag and that both artifacts carry
  the vendored spec under `_data/`.

## 0.1.0

First release.

### Security

- Remote mode no longer writes an `NCBI_API_KEY` (or contact email) into the
  on-disk response cache or into error messages; the credential is redacted from
  the request URL before it is stored or shown.
- Cache mode and `pull()` reject a snapshot `version` that contains a path
  separator or `..`, so a version label cannot read or write outside the snapshot
  directory.

### Added

- `check_id()` and `is_valid_id()` across 46 sources, with four modes: `pattern`
  (offline shape), `cache` (offline existence against a pinned snapshot), `remote`
  (live existence against a source API), and `existence` (snapshot first, then
  remote, degrading to `pattern` when a source has no resolver).
- Real `hgnc` gene-symbol validation in every mode: a bundled approved-symbol
  snapshot for offline `cache` checks, a genenames.org `remote` resolver, and a
  fuzzy "did you mean" suggestion for a near-miss symbol.
- `report()` and `Report.repair()` to validate and clean a whole column, with a
  `to_frame()` verdict table (pandas, polars, or pyarrow via narwhals).
- `synthesize()` builds a deterministic, labeled "messy column" for any source,
  matching the R `synthesize_ids()`.
- Per-id indeterminate state: `on_error="indeterminate"` leaves an unreachable id
  `valid=None` with the reason in a new `error` field, instead of failing the
  batch. Large remote columns can run concurrently via `BIOBOUNCER_REMOTE_WORKERS`.
- Species and version awareness, retired-identifier detection with a successor
  suggestion, and an `opentargets` GraphQL connector.
- Framework adapters: `checks.is_id` (pandera), `types.Id` (pydantic),
  `gx.ExpectColumnValuesToBeValidId` (Great Expectations), and
  `narwhals.valid_id_mask`. A missing cell is never treated as a failure.
- A `biobouncer` command-line tool that validates ids from arguments, a file, or
  standard input and exits non-zero on any invalid input.

### Notes

- R and Python return identical verdicts for the same input, enforced by a shared
  conformance corpus.
