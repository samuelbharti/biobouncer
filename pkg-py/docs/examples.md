# Examples

Practical recipes. Each one is a short, real task. For the full list of sources
and a valid example id for each, see the [sources cookbook](sources.md).

## Clean a column of identifiers

Split a list into the ones that pass and the ones that do not, keeping order.

```python
import biogate as bg

ids = ["MONDO:0005148", "mondo:5148", "MONDO:0018076", "banana"]
verdicts = bg.is_valid_id(ids, source_db="mondo")

good = [i for i, ok in zip(ids, verdicts) if ok]
bad = [i for i, ok in zip(ids, verdicts) if not ok]
# good -> ['MONDO:0005148', 'MONDO:0018076']
# bad  -> ['mondo:5148', 'banana']
```

## Repair what can be repaired

`check_id` returns a `suggestion` for an input that is invalid but mappable, such
as a lowercase prefix. Use it to fix a column instead of dropping it.

```python
fixed = []
for r in bg.check_id(ids, source_db="mondo"):
    if r.valid:
        fixed.append(r.normalized)
    elif r.suggestion is not None:
        fixed.append(r.suggestion)  # 'mondo:5148' -> 'MONDO:0005148'
    else:
        fixed.append(None)          # 'banana' has no repair
```

## Existence, not just shape

`pattern` mode only checks the shape. To check that an id actually exists, use a
pinned snapshot (`cache`) or the live source (`remote`).

```python
# offline, against the sample snapshot that ships with the package
bg.is_valid_id("MONDO:9999999", source_db="mondo", how="cache", version="sample")
# False: well-formed, but not a real term

# live, against the source API (needs a network)
bg.is_valid_id("ENSG00000139618", source_db="ensembl", how="remote")
```

A failed `remote` lookup raises `bg.RemoteError`. It never returns a silent
`False`, so a network problem cannot be mistaken for an absent id.

## Species context

For species-aware sources, pass `species`. For Ensembl the species is encoded in
the id, so even `pattern` mode can reject a well-formed id from the wrong
species.

```python
bg.is_valid_id("ENSMUSG00000059552", source_db="ensembl", species="mus_musculus")
# True
bg.is_valid_id("ENSMUSG00000059552", source_db="ensembl", species="homo_sapiens")
# False
```

## Validate a DataFrame with pandera

`biogate.checks.is_id` returns a pandera `Check`, so a whole column is validated
against a source. Install the adapters with `pip install "biogate[adapters]"`.

```python
import pandas as pd
import pandera.pandas as pa
from biogate.checks import is_id

schema = pa.DataFrameSchema(
    {
        "disease": pa.Column(str, is_id(source_db="mondo")),
        "gene": pa.Column(str, is_id(source_db="ensembl", species="homo_sapiens")),
    }
)

df = pd.DataFrame(
    {"disease": ["MONDO:0005148"], "gene": ["ENSG00000139618"]}
)
schema.validate(df)  # raises pandera.errors.SchemaError on a bad value
```

## Validate a model with pydantic

`biogate.types.Id` returns a validating string type for a field.

```python
from pydantic import BaseModel
from biogate.types import Id

MondoId = Id("mondo")
EnsemblId = Id("ensembl", species="homo_sapiens")


class Association(BaseModel):
    disease: MondoId
    gene: EnsemblId


Association(disease="MONDO:0005148", gene="ENSG00000139618")
# a bad value raises pydantic.ValidationError
```

## Discover sources in code

You never need to hard-code a key or guess an example. `source_info` lists every
source with a valid example and its supported modes.

```python
for row in bg.source_info():
    print(f"{row['key']:15} {row['example']:22} {row['modes']}")
```
