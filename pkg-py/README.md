# biobouncer <img src="https://raw.githubusercontent.com/samuelbharti/biobouncer/main/pkg-r/man/figures/logo.png" align="right" height="150" alt="biobouncer logo" />

> A gate for biological inputs. Validate gene symbols, ontology terms, variant
> formats, and database identifiers, the same way, with the same answer, in
> both **R** and **Python**.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21346522.svg)](https://doi.org/10.5281/zenodo.21346522)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/samuelbharti/biobouncer/blob/main/LICENSE)

This is the Python package. A companion [R package](https://www.samuelbharti.com/biobouncer/r/)
is built alongside it, and the two are held to the same verdict for the same
input by a shared conformance corpus.

> **Status: pre-1.0.** The public API is in use and documented. It may still
> change before the 1.0 release.

## Install

```sh
pip install biobouncer
```

The framework adapters are optional extras:

```sh
pip install "biobouncer[adapters]"   # pandera and pydantic
pip install "biobouncer[gx]"         # Great Expectations
pip install "biobouncer[narwhals]"   # column checks over pandas, polars, or pyarrow
```

## Usage

```python
import biobouncer

# List what can be checked.
biobouncer.sources()

# pattern mode: is the string well-formed?
biobouncer.check_id(["MONDO:0005148", "mondo:5148"], source_db="mondo")

# cache mode: does the id exist in a pinned snapshot, offline?
biobouncer.check_id("MONDO:0005148", source_db="mondo", how="cache", version="sample")
```

`check_id()` returns a list of `Result` records, one per input, in the order given.
A missing input stays missing rather than turning into a quiet `False`.

To validate and clean a whole column in one call:

```python
r = biobouncer.report(["MONDO:0005148", "mondo:5148", "NOTANID", None], source_db="mondo")

r.summary
# {'total': 4, 'valid': 1, 'invalid': 2, 'repairable': 1, 'missing': 1, 'indeterminate': 0}

r.repair()  # substitute the repairable values, leave everything else alone
# ['MONDO:0005148', 'MONDO:0005148', 'NOTANID', None]

r.to_frame()  # a verdict table (pandas, polars, or pyarrow via narwhals)
#            input  valid     normalized     suggestion error
# 0  MONDO:0005148   True  MONDO:0005148            NaN  None
# 1     mondo:5148  False            NaN  MONDO:0005148  None
# 2        NOTANID  False            NaN            NaN  None
# 3            NaN   None            NaN            NaN  None
```

Checks run in four modes: `pattern` (offline shape), `cache` (offline existence
against a pinned snapshot), `remote` (live existence against the source API), and
`existence` (snapshot first, then remote). Snapshots ship with the package, so the
offline modes work with no setup and no network. `biobouncer.pull()` refreshes one
to a newer dated release when you want it.

There is also a `biobouncer` command line tool that exits non-zero on any invalid
input, for use in a pipeline or in CI.

## Documentation

Full documentation is at
[samuelbharti.com/biobouncer/py](https://www.samuelbharti.com/biobouncer/py/),
including the source list, the caching and snapshot guide, and the adapter
reference.

## Contributing

The package is developed in the
[biobouncer monorepo](https://github.com/samuelbharti/biobouncer) alongside the R
package and the shared spec. See
[CONTRIBUTING.md](https://github.com/samuelbharti/biobouncer/blob/main/CONTRIBUTING.md)
to get set up, and
[open an issue](https://github.com/samuelbharti/biobouncer/issues) for a bug or a
source request.

## Citation

If you use biobouncer in your work, please cite it. The DOI above always resolves
to the latest release; see
[CITATION.cff](https://github.com/samuelbharti/biobouncer/blob/main/CITATION.cff)
for the current version and a per-version DOI. A preprint is in preparation.

## License

MIT. See
[LICENSE](https://github.com/samuelbharti/biobouncer/blob/main/LICENSE).
