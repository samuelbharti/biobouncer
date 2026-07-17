# Changelog

All notable changes to the Python package are recorded here. The R package keeps
a matching changelog in `pkg-r/NEWS.md`; the two packages share one version.

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
