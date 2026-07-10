# biogate

> A gate for biological inputs. Validate gene symbols, ontology terms, variant
> formats, and database identifiers — the same way, with the same answer, in
> both **R** and **Python**.

<!-- Badges (fill in once published) -->
<!--
[![CRAN status](https://www.r-pkg.org/badges/version/biogate)](https://cran.r-project.org/package=biogate)
[![PyPI version](https://img.shields.io/pypi/v/biogate)](https://pypi.org/project/biogate/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
-->

> **Status: early development.** The API described below is the intended public
> surface and may change before the first tagged release.

**Documentation:** [R package](https://www.samuelbharti.com/biogate/r/) (pkgdown)
and [Python package](https://www.samuelbharti.com/biogate/py/) (MkDocs), from
one [landing page](https://www.samuelbharti.com/biogate/).

---

## Why biogate

If you build analyses or Shiny/Dash apps in computational biology, you keep
rewriting the same guards: *is this a real gene symbol? a well-formed MONDO ID?
a valid HGVS string? an Open Targets ID that actually exists?* Those checks end
up scattered across projects as ad-hoc regexes and utility functions, and the R
version and the Python version quietly disagree on edge cases.

`biogate` puts those checks in one place, behind one small API, and guarantees
that R and Python give the **same verdict** for the same input by testing both
against a shared conformance corpus. It does not try to replace annotation
engines like biomaRt, ensembldb, or mygene — it validates *inputs* before they
reach those tools.

## Key features

- **One entry point, many sources.** `check_id()` / `is_valid_id()` work across
  a growing set of databases and ontologies (MONDO, EFO, Open Targets, HGNC,
  Ensembl, RefSeq, dbSNP, UniProt, ChEBI, GO, HGVS, …) selected with a single
  `source_db` argument.
- **Three checking modes.** Choose how strict and how online you want to be:
  `pattern` (offline regex/grammar), `cache` (offline existence against a pinned
  snapshot), or `remote` (live existence against the source's API).
- **Species-, source-, and version-aware.** Ask not just *"is this valid?"* but
  *"was this valid for this species, in this source, at this version?"*
- **Rich, vectorized results.** Get a per-element table of `valid` /
  `normalized` / `suggestion`, not just a single boolean — so you can filter or
  repair a column, not just reject one field.
- **Plugs into the tools you already use.** Adapters for `pandera`, `pydantic`,
  `shinyvalidate`, `checkmate`, and `assertr`/`validate`/`pointblank`.
- **Reproducible by design.** `pattern` and `cache` modes are pure functions of
  pinned data; every result records the snapshot version it came from.

## Installation

`biogate` lives in a monorepo; the R package is in the `pkg-r/` subdirectory and
the Python package in `pkg-py/`. Users never see that — just point the installer at
the right subdirectory (or use a published channel).

**R**

```r
# R-universe — binary installs, recommended before the first CRAN release
install.packages("biogate", repos = "https://samuelbharti.r-universe.dev")

# CRAN (once released)
install.packages("biogate")

# development version from GitHub (package is in the pkg-r/ subdirectory)
pak::pak("samuelbharti/biogate/pkg-r")
# or: remotes::install_github("samuelbharti/biogate", subdir = "pkg-r")
```

**Python**

```bash
pip install biogate

# development version from GitHub (package is in the pkg-py/ subdirectory)
pip install "git+https://github.com/samuelbharti/biogate.git#subdirectory=pkg-py"
```

## Quickstart

**R**

```r
library(biogate)

# 1. pattern mode — offline, deterministic, no reference data
is_valid_id("MONDO:0005148", source_db = "mondo", how = "pattern")
#> [1] TRUE

# 2. cache mode — existence against a pinned local snapshot
is_valid_id("MONDO:0005148", source_db = "mondo", how = "cache",
            version = "2024-09")
#> [1] TRUE

# 3. remote mode — live existence check against the source
is_valid_id("ENSG00000139618", source_db = "ensembl", how = "remote",
            species = "homo_sapiens")
#> [1] TRUE

# Rich, vectorized result over a whole column
check_id(
  c("MONDO:0005148", "MONDO:9999999", "mondo:5148"),
  source_db = "mondo",
  how       = "cache",
  version   = "2024-09"
)
#> # A tibble: 3 x 8
#>   input          valid normalized     suggestion    source_db version species how
#>   <chr>          <lgl> <chr>          <chr>         <chr>     <chr>   <chr>   <chr>
#> 1 MONDO:0005148  TRUE  MONDO:0005148  NA            mondo     2024-09 NA      cache
#> 2 MONDO:9999999  FALSE NA             NA            mondo     2024-09 NA      cache
#> 3 mondo:5148     FALSE NA             MONDO:0005148 mondo     2024-09 NA      cache
```

**Python**

```python
import biogate as bg

bg.is_valid_id("MONDO:0005148", source_db="mondo", how="pattern")
# True

bg.is_valid_id(
    "ENSG00000139618", source_db="ensembl", how="remote",
    species="homo_sapiens",
)
# True

# Vectorized: returns a DataFrame (pandas or polars) of per-element results
bg.check_id(
    ["MONDO:0005148", "MONDO:9999999", "mondo:5148"],
    source_db="mondo", how="cache", version="2024-09",
)
```

## The three checking modes

| Mode      | What it answers                                   | Network | Reproducible | Speed |
|-----------|---------------------------------------------------|:-------:|:------------:|:-----:|
| `pattern` | Is the string **well-formed** for this source?    |   no    |     yes      | fast  |
| `cache`   | Does the ID **exist** in a pinned local snapshot? |   no    |     yes      | fast  |
| `remote`  | Does the ID **exist right now** in the source?    |  yes    |      no      | slow  |

`how = "existence"` is a convenience that tries `cache` first and falls back to
`remote` if no local snapshot is available.

The split matters for reproducibility: `pattern` and `cache` are pure functions
of code and pinned data, so the same call always returns the same answer.
`remote` reflects the live source and can change between runs — every result
records which mode and snapshot produced it.

## Species, source, and version awareness

Identifiers are not valid in a vacuum. A symbol can be current in one species
and meaningless in another; an ID can exist in one release of a source and be
retired in the next. `biogate` makes these explicit arguments:

```r
# Same accession, different species contexts
check_id("ENSMUSG00000059552", source_db = "ensembl",
         species = "mus_musculus",  how = "remote")   # valid
check_id("ENSMUSG00000059552", source_db = "ensembl",
         species = "homo_sapiens", how = "remote")    # not a human ID

# Version-aware: was this symbol valid at a specific HGNC release?
check_id("LEPRE1", source_db = "hgnc", how = "cache", version = "2014-11")
#> valid = TRUE  (this symbol was later replaced by P3H1)
check_id("LEPRE1", source_db = "hgnc", how = "cache", version = "2024-09")
#> valid = FALSE, suggestion = "P3H1"
```

- `species` accepts a name (`"homo_sapiens"`) or an NCBI Taxonomy ID (`9606`).
- `version` accepts a source release tag or snapshot date; omit it to use the
  package's default pinned snapshot.
- Both are ignored (with a note) by sources for which they don't apply.

## Result schema

Every `check_id()` row carries enough context to be self-describing:

| column       | meaning                                                        |
|--------------|----------------------------------------------------------------|
| `input`      | the original value, unchanged                                  |
| `valid`      | logical verdict                                                |
| `normalized` | canonical form when valid (e.g. case/prefix normalized)        |
| `suggestion` | best-effort correction when invalid but mappable               |
| `source_db`  | source the check ran against                                   |
| `version`    | snapshot/release that produced the answer                      |
| `species`    | species context, when applicable                               |
| `how`        | mode used (`pattern` / `cache` / `remote`)                     |

## Supported sources (growing)

| `source_db`   | Source                     | Example ID                 | pattern | cache | remote | species-aware |
|---------------|----------------------------|----------------------------|:-------:|:-----:|:------:|:-------------:|
| `hgnc`        | HGNC gene symbols          | `TP53`                     |   ~     |   ✓   |   ✓    |   human/mouse |
| `ensembl`     | Ensembl gene/transcript    | `ENSG00000141510`          |   ✓     |   ✓   |   ✓    |      ✓        |
| `refseq`      | RefSeq accessions          | `NM_000546`                |   ✓     |   ✓   |   ✓    |      ✓        |
| `dbsnp`       | dbSNP variants             | `rs7412`                   |   ✓     |   ~   |   ✓    |      ✓        |
| `hgvs`        | HGVS variant descriptions  | `NM_000546.6:c.215C>G`     |   ✓†    |   —   |   ✓    |      —        |
| `mondo`       | MONDO disease ontology     | `MONDO:0005148`            |   ✓     |   ✓   |   ✓    |      —        |
| `efo`         | Experimental Factor Ont.   | `EFO:0000400`              |   ✓     |   ✓   |   ✓    |      —        |
| `opentargets` | Open Targets IDs           | `ENSG00000141510`          |   ✓     |   ✓   |   ✓    |      —        |
| `uniprot`     | UniProt accessions         | `P04637`                   |   ✓     |   ✓   |   ✓    |      ✓        |
| `chebi`       | ChEBI compounds            | `CHEBI:15377`              |   ✓     |   ✓   |   ✓    |      —        |
| `go`          | Gene Ontology terms        | `GO:0006915`               |   ✓     |   ✓   |   ✓    |      —        |

`✓` supported · `~` partial · `—` not applicable · `†` grammar-based, not a
single regex. Identifier patterns are sourced from the maintained
Identifiers.org / Bioregistry registries where available.

## Integrating with your stack

`biogate` provides the domain checks; your existing validation framework
provides the plumbing.

**pandera (Python)**

```python
import pandera.pandas as pa
import biogate as bg

schema = pa.DataFrameSchema({
    "disease_id": pa.Column(str, bg.checks.is_id(source_db="mondo", how="cache")),
    "target_id":  pa.Column(str, bg.checks.is_id(source_db="ensembl",
                                                 species="homo_sapiens")),
})
```

**pydantic (Python)**

```python
from pydantic import BaseModel
from biogate.types import Id

class Association(BaseModel):
    disease: Id("mondo", how="pattern")
    target:  Id("ensembl", species="homo_sapiens", how="cache")
```

**shinyvalidate (R)**

```r
iv <- InputValidator$new()
iv$add_rule("gene", sv_biogate(source_db = "hgnc", how = "cache"))
iv$enable()
```

**checkmate / assertr (R)**

```r
# stop early in a pipeline
assert_id(df$disease, source_db = "mondo", how = "cache")

# assertr verb inside a dplyr chain
df |> assertr::verify(is_valid_id(disease, source_db = "mondo", how = "cache"))
```

## Design principles

- **Intrinsic before extrinsic.** Format checks (`pattern`) are the fast,
  offline, always-reproducible core. Existence checks (`cache`, `remote`) are
  opt-in and clearly separated.
- **Reproducibility is not optional.** Offline modes are pure functions of
  pinned snapshots; results always report the version they came from.
- **Cross-language parity is a test, not a promise.** A shared corpus of
  input/expected-verdict cases is run against both the R and Python
  implementations in CI.
- **Rich results over booleans.** Return what failed, what it normalizes to, and
  what it should probably be.
- **Compose, don't compete.** Ship adapters into the frameworks people already
  use rather than another standalone validator.

## Reference data & caching

Offline `cache` mode reads versioned snapshots of source identifier sets.
Snapshots are pinned (never auto-updated silently) so analyses stay
reproducible, and are distributed separately from the code so they can be
refreshed without a package release:

```r
biogate_snapshots()                       # list installed snapshots
biogate_pull("mondo", version = "2024-09") # fetch/refresh a snapshot
biogate_cache_dir()                        # where snapshots live
```

`remote` mode caches responses locally and respects each source's rate limits.

## Roadmap

- [ ] `pattern` mode + core API + result schema
- [ ] Shared conformance corpus + R/Python parity CI
- [ ] `cache` mode + snapshot tooling for the initial source set
- [ ] `remote` resolvers (OLS, Ensembl REST, Open Targets, UniProt, dbSNP)
- [ ] Species and version awareness across applicable sources
- [ ] Framework adapters (pandera, pydantic, shinyvalidate, checkmate, assertr)
- [ ] HGVS grammar validator
- [ ] First tagged releases on PyPI and CRAN/R-universe

## Contributing

Adding a source should be small and declarative: a prefix, a pattern, optional
species/version metadata, and (optionally) a cache builder and a remote
resolver. See `CONTRIBUTING.md` and the source-registry spec in `PLAN.md`.

## License

MIT © biogate authors.

## Citation

If `biogate` supports your work, please cite it (a `CITATION` file will be
provided with the first release).
