# biobouncer

> A gate for biological inputs. Validate gene symbols, ontology terms, variant
> formats, and database identifiers — the same way, with the same answer, in
> both **R** and **Python**.

<!-- Badges (fill in once published) -->
<!--
[![CRAN status](https://www.r-pkg.org/badges/version/biobouncer)](https://cran.r-project.org/package=biobouncer)
[![PyPI version](https://img.shields.io/pypi/v/biobouncer)](https://pypi.org/project/biobouncer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
-->

> **Status: early development.** The API described below is the intended public
> surface and may change before the first tagged release.

**Documentation:** [R package](https://www.samuelbharti.com/biobouncer/r/) (pkgdown)
and [Python package](https://www.samuelbharti.com/biobouncer/py/) (MkDocs), from
one [landing page](https://www.samuelbharti.com/biobouncer/).

---

## Why biobouncer

If you build analyses or Shiny/Dash apps in computational biology, you keep
rewriting the same guards: *is this a real gene symbol? a well-formed MONDO ID?
a valid HGVS string? a UniProt accession that actually exists?* Those checks end
up scattered across projects as ad-hoc regexes and utility functions, and the R
version and the Python version quietly disagree on edge cases.

`biobouncer` puts those checks in one place, behind one small API, and guarantees
that R and Python give the **same verdict** for the same input by testing both
against a shared conformance corpus. It does not try to replace annotation
engines like biomaRt, ensembldb, or mygene — it validates *inputs* before they
reach those tools.

## Key features

- **One entry point, many sources.** `check_id()` / `is_valid_id()` work across
  45 databases and ontologies (MONDO, EFO, HGNC, Ensembl, RefSeq, dbSNP, UniProt,
  ChEBI, GO, HGVS, and more) selected with a single `source_db` argument.
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
- **Works from the shell.** The Python package installs a `biobouncer` command that
  validates ids from a file or a pipe and exits non-zero on any invalid input,
  for use in scripts and CI.
- **Reproducible by design.** `pattern` and `cache` modes are pure functions of
  pinned data; every result records the snapshot version it came from.

## Installation

`biobouncer` lives in a monorepo; the R package is in the `pkg-r/` subdirectory and
the Python package in `pkg-py/`. Users never see that — just point the installer at
the right subdirectory (or use a published channel).

**R**

```r
# R-universe — binary installs, recommended before the first CRAN release
install.packages("biobouncer", repos = "https://samuelbharti.r-universe.dev")

# CRAN (once released)
install.packages("biobouncer")

# development version from GitHub (package is in the pkg-r/ subdirectory)
pak::pak("samuelbharti/biobouncer/pkg-r")
# or: remotes::install_github("samuelbharti/biobouncer", subdir = "pkg-r")
```

**Python**

```bash
pip install biobouncer

# development version from GitHub (package is in the pkg-py/ subdirectory)
pip install "git+https://github.com/samuelbharti/biobouncer.git#subdirectory=pkg-py"
```

## Quickstart

**R**

```r
library(biobouncer)

# 1. pattern mode — offline, deterministic, no reference data
is_valid_id("MONDO:0005148", source_db = "mondo", how = "pattern")
#> [1] TRUE

# 2. cache mode — existence against a pinned local snapshot
is_valid_id("MONDO:0005148", source_db = "mondo", how = "cache",
            version = "sample")
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
  version   = "sample"
)
#> # A tibble: 3 x 8
#>   input          valid normalized     suggestion    source_db version species how
#>   <chr>          <lgl> <chr>          <chr>         <chr>     <chr>   <chr>   <chr>
#> 1 MONDO:0005148  TRUE  MONDO:0005148  NA            mondo     sample  NA      cache
#> 2 MONDO:9999999  FALSE NA             NA            mondo     sample  NA      cache
#> 3 mondo:5148     FALSE NA             MONDO:0005148 mondo     sample  NA      cache
```

**Python**

```python
import biobouncer as bg

bg.is_valid_id("MONDO:0005148", source_db="mondo", how="pattern")
# True

bg.is_valid_id(
    "ENSG00000139618", source_db="ensembl", how="remote",
    species="homo_sapiens",
)
# True

# Vectorized: returns a list of per-element Result records, in input order
bg.check_id(
    ["MONDO:0005148", "MONDO:9999999", "mondo:5148"],
    source_db="mondo", how="cache", version="sample",
)
```

## Clean a column

The everyday job is a whole column: which values are wrong, and can you fix the
ones you can. `report_id()` / `report()` validate the column and print a summary;
`repair_id()` / `Report.repair()` substitute the fixable values (a withdrawn gene
symbol becomes its successor) and leave valid, unmappable, and missing values
untouched. In cache mode the snapshot version defaults to the latest installed,
so you do not have to name one.

**R**

```r
genes <- c("TP53", "MLL", "notagene", NA)

report_id(genes, "hgnc", how = "cache")
#> # biobouncer report on hgnc (cache mode): 1 valid, 1 repairable, 1 invalid, 1 missing of 4
#> # A tibble: 4 x 8
#>   input      valid normalized suggestion source_db version    species how
#>   <chr>      <lgl> <chr>      <chr>      <chr>     <chr>      <chr>   <chr>
#> 1 TP53       TRUE  TP53       NA         hgnc      2026-07-07 NA      cache
#> 2 MLL        FALSE NA         KMT2A      hgnc      2026-07-07 NA      cache
#> 3 notagene   FALSE NA         NA         hgnc      2026-07-07 NA      cache
#> 4 NA         NA    NA         NA         hgnc      2026-07-07 NA      cache

repair_id(genes, "hgnc", how = "cache")
#> [1] "TP53"     "KMT2A"    "notagene" NA
```

**Python**

```python
genes = ["TP53", "MLL", "notagene", None]

rep = bg.report(genes, "hgnc", how="cache")
rep
# <biobouncer report on 'hgnc' (cache mode): 1 valid, 1 repairable, 1 invalid, 1 missing of 4>

rep.repair()
# ['TP53', 'KMT2A', 'notagene', None]
```

`report`/`report_id` are for inspecting and cleaning; to enforce validity inside
a framework (pandera, Great Expectations, pydantic, shiny) use the adapters.

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
retired in the next. `biobouncer` makes these explicit arguments:

```r
# Same accession, different species contexts
check_id("ENSMUSG00000059552", source_db = "ensembl",
         species = "mus_musculus",  how = "remote")   # valid
check_id("ENSMUSG00000059552", source_db = "ensembl",
         species = "homo_sapiens", how = "remote")    # not a human ID

# Retired symbols map to their approved successor
check_id("MLL", source_db = "hgnc", how = "cache", version = "sample")
#> valid = FALSE, suggestion = "KMT2A"  (MLL was renamed KMT2A)
```

- `species` accepts a name (`"homo_sapiens"`) or an NCBI Taxonomy ID (`9606`). It
  is enforced by the sources for which it applies (such as Ensembl and UniProt)
  and ignored by the rest.
- `version` selects the snapshot for `cache` mode. The packages ship a small
  `sample` snapshot; `biobouncer_pull()` fetches full, dated snapshots for the OBO
  ontologies.

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
| `how`        | mode used (`pattern` / `cache` / `remote` / `existence`)       |

## Supported sources (growing)

biobouncer checks 46 sources. A selection is shown below; run `source_info()` or see
the [sources cookbook](https://www.samuelbharti.com/biobouncer/py/sources/) for the
full list with the modes each source supports.

| `source_db`    | Source                     | Example ID                 | pattern | cache | remote | species-aware |
|----------------|----------------------------|----------------------------|:-------:|:-----:|:------:|:-------------:|
| `mondo`        | MONDO disease ontology     | `MONDO:0005148`            |   ✓     |   ✓   |   ✓    |      —        |
| `efo`          | Experimental Factor Ont.   | `EFO:0000400`              |   ✓     |   ✓   |   ✓    |      —        |
| `go`           | Gene Ontology terms        | `GO:0006915`               |   ✓     |   ✓   |   ✓    |      —        |
| `chebi`        | ChEBI compounds            | `CHEBI:15377`              |   ✓     |   ✓   |   ✓    |      —        |
| `hgnc`         | HGNC gene symbols          | `TP53`                     |   ~     |   ✓   |   ✓    |      —        |
| `ensembl`      | Ensembl gene/transcript    | `ENSG00000139618`          |   ✓     |   —   |   ✓    |      ✓        |
| `opentargets`  | Open Targets targets       | `ENSG00000139618`          |   ✓     |   —   |   ✓    |      —        |
| `refseq`       | RefSeq accessions          | `NM_000546.6`              |   ✓     |   —   |   ✓    |      —        |
| `uniprot`      | UniProt accessions         | `P04637`                   |   ✓     |   —   |   ✓    |      ✓        |
| `dbsnp`        | dbSNP variants             | `rs7412`                   |   ✓     |   —   |   ✓    |      —        |
| `hgvs`         | HGVS variant syntax        | `NM_004006.2:c.4375C>T`    |   ✓†    |   —   |   ✓    |      —        |

`✓` supported · `~` shape check only, a loose token match · `—` not available ·
`†` syntax only, a single regex (not coordinate-level validation). The Open
Targets connector checks whether a human Ensembl gene id is a target the platform
covers, through its GraphQL API. Identifier patterns come from the
Identifiers.org / Bioregistry registries where available.

## Integrating with your stack

`biobouncer` provides the domain checks; your existing validation framework
provides the plumbing.

**pandera (Python)**

```python
import pandera.pandas as pa
import biobouncer as bg

schema = pa.DataFrameSchema({
    "disease_id": pa.Column(str, bg.checks.is_id(source_db="mondo", how="cache",
                                                 version="sample")),
    "target_id":  pa.Column(str, bg.checks.is_id(source_db="ensembl",
                                                 species="homo_sapiens")),
})
```

**pydantic (Python)**

```python
from pydantic import BaseModel
from biobouncer.types import Id

class Association(BaseModel):
    disease: Id("mondo", how="pattern")
    target:  Id("ensembl", species="homo_sapiens", how="pattern")
```

**shinyvalidate (R)**

```r
iv <- InputValidator$new()
iv$add_rule("gene", sv_biobouncer(source_db = "hgnc", how = "cache", version = "sample"))
iv$enable()
```

**checkmate / assertr (R)**

```r
# stop early in a pipeline
assert_valid_id(df$disease, source_db = "mondo", how = "cache", version = "sample")

# assertr verb inside a dplyr chain
df |> assertr::verify(
  is_valid_id(disease, source_db = "mondo", how = "cache", version = "sample")
)
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
biobouncer_snapshots()          # list installed snapshots
biobouncer_pull("mondo")        # fetch the current MONDO snapshot
biobouncer_cache_dir()          # where snapshots live
```

`remote` mode caches responses locally and respects each source's rate limits.

## Roadmap

Delivered:

- [x] `pattern` mode, the core API, and the rich result schema
- [x] Shared conformance corpus with R and Python parity
- [x] `cache` mode and snapshot tooling for the OBO ontologies
- [x] `remote` resolvers (OLS, Ensembl, UniProt, NCBI, EBI, and more: 17 resolvers across 39 sources)
- [x] Species and version awareness
- [x] Framework adapters (pandera, pydantic, Great Expectations, narwhals; shinyvalidate, checkmate, assertr/validate/pointblank)
- [x] HGVS syntax validator
- [x] Command-line interface
- [x] Real gene-symbol validation (a full HGNC snapshot and a genenames.org resolver)
- [x] Fuzzy "did you mean" suggestions
- [x] A validate-and-repair report for data-frame columns (`report` / `report_id`)
- [x] Per-id indeterminate state and concurrent large-column remote checks
- [x] An Open Targets connector (GraphQL)

Planned:

- [ ] First tagged releases on PyPI and CRAN / R-universe

## Contributing

Adding a source should be small and declarative: a prefix, a pattern, optional
species/version metadata, and (optionally) a cache builder and a remote
resolver. See `CONTRIBUTING.md` and the source-registry spec in `PLAN.md`.

## License

MIT © biobouncer authors.

## Citation

If `biobouncer` supports your work, please cite it. See `CITATION.cff` for citation
metadata.
