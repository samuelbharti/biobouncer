# Guide

This guide covers the checking modes, species and version awareness, HGVS
syntax, and the validation framework adapters. Every example that does not call
a network runs offline.

## The checking modes

`how` selects how strict and how online the check is.

| Mode        | What it answers                                   | Network |
| ----------- | ------------------------------------------------- | :-----: |
| `pattern`   | Is the string well-formed for this source?        |   no    |
| `cache`     | Does the id exist in a pinned local snapshot?     |   no    |
| `remote`    | Does the id exist right now in the source?        |   yes   |
| `existence` | Snapshot when available, otherwise remote.        | maybe   |

### pattern

The default. Offline shape check, no reference data.

```python
import biobouncer as bg

bg.is_valid_id("MONDO:0005148", source_db="mondo", how="pattern")
# True
```

### cache

`cache` mode checks existence against a pinned, offline snapshot. A small
`sample` snapshot ships with the package, so the example below needs no
download. A real analysis pins a dated snapshot instead.

```python
for r in bg.check_id(
    ["MONDO:0005148", "MONDO:9999999"],
    source_db="mondo",
    how="cache",
    version="sample",
):
    print(r.input, r.valid)
# MONDO:0005148 True
# MONDO:9999999 False
```

`MONDO:9999999` is well-formed, so it passes `pattern`, but it is not in the
snapshot, so it fails `cache`. Choosing the mode is choosing how strict the
check is. Snapshots are managed with `pull`, `snapshots`, and `cache_dir`.

### remote

`remote` mode checks existence live against a source API. It needs a network, so
it is not run here, but the call looks like this:

```python
bg.check_id("ENSG00000139618", source_db="ensembl", how="remote")
```

A network failure in `remote` mode raises `RemoteError`. It never returns a
silent `False`, so a failed lookup cannot be mistaken for an absent identifier.
Every extrinsic result records the snapshot version or the timestamp that
produced it.

Pass `on_error="indeterminate"` to keep going when one id is unreachable: that id
comes back `valid=None` with the reason in its `error` field, and the rest of the
column is still checked.

```python
bg.check_id(genes, source_db="hgnc", how="remote", on_error="indeterminate")
```

Checking a large column live is faster with several requests in flight. Set
`BIOBOUNCER_REMOTE_WORKERS` to the number of concurrent lookups (the default is `1`,
sequential). Concurrency never changes a verdict, only the order the network is
touched, and per-host politeness still applies: NCBI E-utilities are held to
three requests a second, or ten when `NCBI_API_KEY` is set.

## Species and version awareness

Some sources are species-aware. For Ensembl the species is encoded in the id, so
`pattern` mode can reject a well-formed id that belongs to the wrong species.

```python
# ENSMUSG is a mouse gene id.
bg.is_valid_id("ENSMUSG00000059552", source_db="ensembl", species="mus_musculus")
# True
bg.is_valid_id("ENSMUSG00000059552", source_db="ensembl", species="homo_sapiens")
# False
```

`species` accepts a name such as `"homo_sapiens"` or an NCBI taxon id such as
`9606`. A source that is not species-aware ignores the argument.

## HGVS variant syntax

The `hgvs` source checks the syntax of an HGVS sequence variant name. This is a
grammar check in `pattern` mode. It confirms the shape of the variant. It does
not check coordinates or that the variant exists.

```python
bg.is_valid_id(
    [
        "NM_004006.2:c.4375C>T",
        "NP_003997.1:p.(Gly56Ala)",
        "NM_004006.2:c.76insG",
    ],
    source_db="hgvs",
)
# [True, True, False]
```

The last one is invalid: an insertion must sit between two flanking positions,
so it needs a range such as `c.76_77insG`. `remote` mode looks a variant up
against the Mutalyzer normalizer, which goes beyond the offline syntax check.

## Framework adapters

The adapters wrap the core classifier so it plugs into common validation
frameworks. They never reimplement any checks. Install them with
`pip install "biobouncer[adapters]"`.

### pandera

`biobouncer.checks.is_id` returns a pandera `Check` for a column of identifiers.

```python
import pandas as pd
import pandera.pandas as pa
from biobouncer.checks import is_id

schema = pa.DataFrameSchema(
    {
        "disease_id": pa.Column(str, is_id(source_db="mondo")),
        "target_id": pa.Column(str, is_id(source_db="ensembl", species="homo_sapiens")),
    }
)

df = pd.DataFrame(
    {"disease_id": ["MONDO:0005148"], "target_id": ["ENSG00000141510"]}
)
schema.validate(df)
```

### pydantic

`biobouncer.types.Id` returns a validating string type. Use it as a field
annotation, most readably through an alias.

```python
from pydantic import BaseModel
from biobouncer.types import Id

MondoId = Id("mondo")


class Association(BaseModel):
    disease: MondoId


Association(disease="MONDO:0005148")
```

A value that is not valid for the source raises a pydantic `ValidationError`.

## Generating test data

`synthesize` builds a labeled "messy column" for any source, so you can exercise a
validation pipeline without hand-writing test ids:

```python
import biobouncer as bg

rows = bg.synthesize("mondo")
# each row has input, category (valid/repairable/invalid/missing), and the
# pattern-mode valid/normalized/suggestion for that input
column = [row["input"] for row in rows]
bg.report(column, "mondo").summary
```

The column is deterministic and offline, and the R `synthesize_ids()` produces the
same one. `ec`, `hgvs`, and `hgnc` have no repairable form, so they omit that
category. Pass `how="cache"` for a snapshot-mode column, where a repairable value
can be a retired id that maps to its successor.

## Summary

- `pattern` checks shape, `cache` and `remote` check existence, and `existence`
  uses a snapshot first and remote as a fallback.
- Results are vectorized and preserve input order and length. Errors are
  explicit, never a silent `False`.
- The same inputs give the same verdicts in the R package, which is enforced by
  a shared conformance corpus.
