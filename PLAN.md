# biogate — Implementation Plan

A build plan for `biogate`, a cross-language (R + Python) validator for
biological identifiers and inputs. This document is written to be handed to
Claude Code (or any implementer): it fixes the architecture, the API contract,
and a phased task list with acceptance criteria. Read it top to bottom before
writing code; each phase has a **Definition of Done**.

> **Status (2026-07):** Phases 0 through 7 are delivered. This document is kept as
> the original design spec, for the architecture and the rationale. A few details
> below describe the original intent and differ from the shipped code: the Python
> package uses flat modules (`core.py`, `_registry.py`, `_pattern.py`, `_cache.py`,
> `_remote.py`), not the `modes/`/`resolvers/` layout in section 3; the source
> schema uses `curie:`/`case:` blocks rather than the `normalize:` and
> `default_version:` keys shown in section 5; and the Open Targets connector is
> planned, not built. For the current, accurate source list and the modes each
> source supports, run `source_info()` or read the package docs.

---

## 1. Goals and non-goals

**Goals**

- Validate biological identifiers/inputs across many sources (ontologies,
  databases, gene symbols, variant formats) behind one small API.
- Three checking modes: `pattern` (offline regex/grammar), `cache` (offline
  existence vs. pinned snapshot), `remote` (live existence vs. source API).
- Species-, source-, and version-aware: answer "valid for *this* species /
  source / version?"
- Identical verdicts in R and Python, enforced by a shared conformance corpus.
- Rich, vectorized results (`valid` / `normalized` / `suggestion`), not booleans.
- Adapters into `pandera`, `pydantic`, `shinyvalidate`, `checkmate`, `assertr`.

**Non-goals (explicitly out of scope)**

- **No Rust / no compiled core.** Pure R and pure Python. Vectorize instead.
- Not an annotation/retrieval engine. We validate inputs; we do not replace
  biomaRt, ensembldb, mygene, etc. `remote` mode may *call* such sources but
  only to answer existence, not to return annotations.
- No reference-base or coordinate-level HGVS validation in v1 (grammar/syntax
  only; deeper HGVS checks are a later phase).

---

## 2. Core concepts

**Intrinsic vs. extrinsic.** `pattern` is intrinsic (pure, offline,
reproducible). `cache` and `remote` are extrinsic (depend on reference data).
Keep the two cleanly separated; extrinsic modes must always report the snapshot
or timestamp that produced the answer.

**One classifier, many adapters.** Each source implements a single vectorized
classifier that returns the result schema below. Everything else — framework
adapters, the convenience predicates — is a thin wrapper over that classifier.
Adapters are written natively per language; only the *logic* is shared, via the
corpus (§7), not shared binaries.

**Reproducibility.** Snapshots are pinned and never silently auto-update.
Distributed separately from code so they can be refreshed without a release.

---

## 3. Repository layout

Monorepo, one source of truth for shared assets.

```
biogate/                             # ONE monorepo
├── PLAN.md                          # this file
├── README.md
├── CLAUDE.md                        # short conventions digest for agents (§11)
├── shared/                          # SINGLE SOURCE OF TRUTH
│   ├── sources/                     # one declarative YAML per source (§5)
│   │   ├── mondo.yaml
│   │   ├── hgnc.yaml
│   │   └── ...
│   └── corpus/                      # cross-language conformance cases (§7)
│       ├── mondo.cases.jsonl
│       └── ...
├── tools/
│   └── sync_shared.py               # vendors shared/ into each package (§3.1)
├── .github/workflows/               # path-filtered CI (§3.1)
│   ├── r.yml
│   ├── python.yml
│   └── drift.yml
├── pkg-py/                         # biogate (PyPI)
│   ├── src/biogate/
│   │   ├── core.py                  # check_id / is_valid_id, result model
│   │   ├── registry.py              # loads vendored sources
│   │   ├── modes/                   # pattern.py, cache.py, remote.py
│   │   ├── resolvers/               # per-source remote resolvers
│   │   ├── checks.py                # pandera integration
│   │   ├── types.py                 # pydantic integration
│   │   ├── snapshots.py
│   │   └── _data/                   # ← vendored copy of shared/ (generated)
│   └── tests/
└── pkg-r/                           # biogate (CRAN / R-universe)
    ├── R/
    │   ├── check_id.R
    │   ├── registry.R
    │   ├── mode-pattern.R / mode-cache.R / mode-remote.R
    │   ├── resolvers.R
    │   ├── adapters-shinyvalidate.R
    │   └── adapters-assert.R
    ├── inst/extdata/                # ← vendored copy of shared/ (generated)
    └── tests/testthat/
```

**Key rule:** `shared/sources/` and `shared/corpus/` are the single source of
truth. Neither language hard-codes a pattern that isn't in a source file.

### 3.1 Vendoring the shared spec (why and how)

An R build only packages files under `pkg-r/`, and a Python wheel only ships files
under `pkg-py/`; neither can reach a sibling `shared/` folder at install time.
So `shared/` must be **copied into each package before build**:

- `tools/sync_shared.py` copies `shared/` → `pkg-r/inst/extdata/` and
  `pkg-py/src/biogate/_data/`. Run it in the build/release step of both
  packages so the vendored copy is always present and current.
- At runtime, packages read the vendored copy (`system.file("extdata", ...)` in
  R; `importlib.resources` in Python), never `../shared`.
- A **drift check** in CI (`drift.yml`) runs `sync_shared.py` and fails if it
  produces any diff — i.e. someone edited a vendored copy directly, or forgot to
  re-sync after editing `shared/`. This keeps R and Python provably in lockstep.
- **Path-filtered CI:** `r.yml` triggers on `pkg-r/**` + `shared/**`, `python.yml`
  on `pkg-py/**` + `shared/**`; any `shared/**` change runs both (so the
  conformance corpus is enforced on every spec edit).

---

## 4. Public API contract (both languages)

Two functions, same signature and semantics in R and Python.

```
check_id(x, source_db, how = "pattern",
         species = NULL, version = NULL, ...) -> table (one row per element of x)

is_valid_id(x, source_db, how = "pattern",
            species = NULL, version = NULL, ...) -> logical vector
```

- `x`: scalar or vector/Series of strings.
- `source_db`: key into the source registry (e.g. `"mondo"`, `"ensembl"`).
- `how`: `"pattern"` | `"cache"` | `"remote"` | `"existence"`
  (`"existence"` = cache-then-remote fallback).
- `species`: name (`"homo_sapiens"`) or NCBI taxon ID (`9606`); ignored with a
  note by sources where inapplicable.
- `version`: source release tag / snapshot date; default = package's pinned
  snapshot for that source.

**Result schema** (columns of `check_id`, fields of the row model):

| field        | type     | notes                                             |
|--------------|----------|---------------------------------------------------|
| `input`      | str      | original, unchanged                               |
| `valid`      | bool     | verdict                                           |
| `normalized` | str/NA   | canonical form when valid                         |
| `suggestion` | str/NA   | correction when invalid but mappable              |
| `source_db`  | str      | echoed                                            |
| `version`    | str/NA   | snapshot/release used (NA for pure pattern)       |
| `species`    | str/NA   | context used                                      |
| `how`        | str      | mode used                                         |

`is_valid_id` returns just the `valid` column. Both preserve input order and
length. Invalid `source_db` / `how` raise a clear error; unreachable `remote`
degrades to an informative error (never a silent `FALSE`).

---

## 5. Source registry spec

Each source is one declarative file in `shared/sources/`. Adding a source =
adding a file (plus optional resolver code). Proposed schema:

```yaml
key: mondo
name: MONDO Disease Ontology
description: Monarch Disease Ontology terms.
# pattern mode: unanchored ASCII-class regex so R (PCRE) and Python (re) agree
pattern: "MONDO:[0-9]{7}"
example: "MONDO:0005148"
# metadata
species_aware: false
version_aware: true
# CURIE sources get prefix-case and zero-pad suggestions
curie:
  prefix: MONDO
  pad_to: 7
# cache mode
cache:
  builder: obo             # id of the snapshot builder
  obo_url: http://purl.obolibrary.org/obo/mondo.obo
# remote mode
remote:
  resolver: ols            # id of the remote resolver
  ols_ontology: mondo
provenance:
  pattern_source: bioregistry   # where the pattern came from
  homepage: https://mondo.monarchinitiative.org
```

Patterns should be pulled from the Identifiers.org / Bioregistry registries
where they exist, with `provenance.pattern_source` recording the origin. Do not
invent a regex when a curated one exists.

**Initial source set (Phase 1–4):** `mondo`, `efo`, `hgnc`, `ensembl`,
`refseq`, `dbsnp`, `uniprot`, `chebi`, `go`, `opentargets`. `hgvs` is
syntax-based and handled specially (Phase 7).

---

## 6. Modes — implementation notes

- **pattern:** compile the source regex once; vectorize over the input
  (`grepl`/`stringr` in R; `re` over a pandas/polars Series in Python). Apply
  `normalize` rules to produce `normalized`. No network, no data files.
- **cache:** load the pinned snapshot for `(source_db, version)` — a compact
  set/columnar file of valid IDs (and, where relevant, per-species and
  per-version validity). Membership test is a vectorized join/lookup. If the
  requested `version` snapshot isn't installed, error with instructions to
  `biogate_pull()`.
- **remote:** dispatch to the source's resolver (§ resolvers). Batch requests,
  cache responses on disk, respect rate limits, and set sane timeouts. Network
  failure is an error, not a `FALSE`.

**Resolvers to implement (remote):** OLS (mondo/efo/chebi/go), Ensembl REST
(ensembl, species-aware), Open Targets GraphQL (opentargets), UniProt REST
(uniprot), NCBI/dbSNP (dbsnp, refseq). Each resolver is small and isolated so
sources can be added without touching the core.

---

## 7. Cross-language conformance corpus

The mechanism that guarantees R and Python agree.

- Format: one `*.cases.jsonl` per source in `shared/corpus/`. Each line:

```json
{"input": "mondo:5148", "source_db": "mondo", "how": "pattern",
 "species": null, "version": null,
 "expect": {"valid": false, "suggestion": "MONDO:0005148"},
 "note": "lowercase prefix should fail pattern but be suggestible"}
```

- Both packages have a test that loads every case for their available modes and
  asserts the produced result matches `expect`.
- `pattern` cases are the baseline (fully deterministic). `cache` cases pin a
  `version`. `remote` cases run only in a dedicated, network-flagged CI job (or
  against recorded fixtures) so the default test suite stays offline.
- **Rule:** a new source is not "done" until it has corpus cases covering
  valid, invalid, wrong-case, wrong-species (if applicable), and
  retired-in-newer-version (if applicable).

---

## 8. Phased delivery

### Phase 0 — Scaffolding
- Create the monorepo layout (§3): `shared/`, `pkg-r/`, `pkg-py/`, `tools/`,
  `.github/workflows/`.
- Implement `tools/sync_shared.py` (vendors `shared/` into `pkg-r/inst/extdata/`
  and `pkg-py/src/biogate/_data/`) and wire it into both build steps.
- Add path-filtered CI (`r.yml`, `python.yml`) plus the drift check (`drift.yml`)
  from §3.1; add linting/formatting for both languages.
- Reserve names: confirm `biogate` is free on **PyPI** and **CRAN**, create the
  GitHub repo, and set up **R-universe** as the interim R channel.
- **DoD:** empty packages build, install, and pass an empty test suite in CI on
  Linux/macOS/Windows; the drift check passes; both packages install from GitHub
  subdirectories and from R-universe.

**R-universe registry** — a repo named `YOURACCOUNT.r-universe.dev` containing:

```json
[
  { "package": "biogate", "url": "https://github.com/YOURORG/biogate", "subdir": "pkg-r" }
]
```

Install the R-universe GitHub app on the account; the `subdir` field points the
builder at `pkg-r/`. R-universe then builds Windows/macOS binaries kept in sync
with source. (After biogate reaches CRAN, opt out of duplicate auto-indexing with
`Config/runiverse/noindex: true` in `pkg-r/DESCRIPTION` if desired.)

**Install commands to verify in CI**

```r
# R — published channel
install.packages("biogate", repos = "https://YOURACCOUNT.r-universe.dev")
# R — dev from the monorepo subdirectory
pak::pak("YOURORG/biogate/pkg-r")
remotes::install_github("YOURORG/biogate", subdir = "pkg-r")
```
```bash
# Python — dev from the monorepo subdirectory
pip install "git+https://github.com/YOURORG/biogate.git#subdirectory=pkg-py"
```

### Phase 1 — Core + pattern mode
- Implement `check_id`/`is_valid_id`, the result schema, the registry loader,
  and `pattern` mode in both languages.
- Land the initial source files (§5) with patterns sourced from Bioregistry.
- **DoD:** `pattern` mode works for all initial sources in R and Python;
  identical result schema; input order/length preserved; bad-arg errors.

### Phase 2 — Conformance corpus + parity
- Author corpus cases for every source's `pattern` mode.
- Wire both test suites to consume the corpus.
- **DoD:** both packages pass 100% of `pattern` corpus cases in CI; a
  deliberately divergent implementation is caught by the corpus (verify with a
  temporary failing case).

### Phase 3 — Cache mode + snapshots
- Define the snapshot format and a builder per cacheable source.
- Implement `cache` mode lookup and `biogate_pull()`/`snapshots()`/`cache_dir()`.
- Distribute snapshots separately (release asset / data repo), pinned.
- **DoD:** `cache` mode + `version` argument work for ≥4 sources; corpus `cache`
  cases pass; missing-snapshot path gives an actionable error.

### Phase 4 — Remote mode
- Implement resolvers (OLS, Ensembl REST, Open Targets, UniProt, dbSNP/RefSeq)
  with batching, on-disk response caching, timeouts, and rate limiting.
- Record fixtures for a network-flagged corpus job.
- **DoD:** `remote` mode works for the resolver set; offline default suite still
  passes; network job passes against fixtures; failures error rather than
  silently returning `FALSE`.

### Phase 5 — Species + version awareness
- Thread `species` through pattern/cache/remote where applicable (esp. Ensembl,
  RefSeq, UniProt, dbSNP, HGNC).
- Support version-scoped validity in cache/remote (e.g. retired symbols with
  suggestions, à la HGNChelper's frozen maps).
- **DoD:** species-mismatch and version-retirement corpus cases pass in both
  languages.

### Phase 6 — Framework adapters
- Python: `biogate.checks.is_id(...)` (pandera Check), `biogate.types.Id(...)`
  (pydantic type). Optional Great Expectations expectation.
- R: `sv_biogate(...)` (shinyvalidate rule), `assert_id(...)` (checkmate-style),
  and an `assertr`/`validate`-friendly predicate.
- **DoD:** each adapter has a worked example in docs and a test; adapters call
  the core classifier (no duplicated logic).

### Phase 7 — HGVS grammar, docs, release
- Add a grammar-based `hgvs` validator (syntax only in v1). This is the one
  place where, if profiling ever demands it, a compiled core *could* be
  reconsidered later — but v1 stays pure.
- Write vignettes/notebooks; finalize `README`, `CONTRIBUTING`, `CITATION`.
- Package + release: PyPI, and CRAN (with R-universe as fallback given no Rust
  is involved, CRAN should be straightforward). Evaluate a Bioconductor data
  companion for snapshots if it fits.
- **DoD:** first tagged releases installable from PyPI and CRAN/R-universe with
  passing cross-language parity.

---

## 9. Testing strategy

- **Unit tests** per mode and per source in each language.
- **Conformance corpus** (§7) — the parity guarantee; runs in default CI.
- **Snapshot reproducibility** — same `(source_db, version)` yields identical
  results across runs and machines.
- **Network-isolated by default** — `remote` tests are opt-in / fixture-backed
  so the standard suite is offline and fast.
- **Property checks** — order/length preservation; idempotence of `normalize`.

---

## 10. Risks and mitigations

- **Reference data goes stale.** → Pin snapshots, never auto-update, always
  report `version`; provide `biogate_pull()` to refresh deliberately.
- **Remote APIs drift / rate-limit.** → Isolate resolvers, cache responses,
  back off, and fail loudly rather than returning wrong verdicts.
- **R and Python diverge.** → The corpus is mandatory; no source ships without
  cases; parity runs on every PR.
- **Name/prefix clashes with ontologies (e.g. an Open Targets concept).** →
  Keep `source_db` keys in one registry; validate them against Bioregistry
  prefixes at build time.
- **Scope creep into annotation.** → Enforce the non-goals: existence answers a
  boolean, it does not return annotations.

---

## 11. Conventions (source for CLAUDE.md)

- Pure R and pure Python. No Rust, no compiled extensions.
- One monorepo; the R package is in `pkg-r/`, the Python package in `pkg-py/`.
- Never hard-code a pattern outside `shared/sources/`.
- Never edit a vendored copy (`pkg-r/inst/extdata/`, `pkg-py/src/biogate/_data/`)
  by hand — edit `shared/` and re-run `tools/sync_shared.py`. CI drift check
  enforces this.
- Every extrinsic result must carry its `version`/timestamp.
- Adapters wrap the core classifier; never duplicate validation logic.
- A source is "done" only with: source file + patterns cited + corpus cases +
  (if cacheable) snapshot builder + (if remote) resolver + docs example.
- Default test suite must run fully offline.
- Preserve input order and length; errors are explicit, never silent `FALSE`.
