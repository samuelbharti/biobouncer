# Changelog

All notable changes to the Python package are recorded here. The R package keeps
a matching changelog in `pkg-r/NEWS.md`; the two packages share one version.

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
