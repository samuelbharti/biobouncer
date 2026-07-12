# Clean a column

The most common job is not "is this one id valid" but "here is a column of ids,
which are wrong, and can you fix the ones you can". `report` does that in one
call. It runs [`check_id`](reference.md#checking-identifiers) over the whole
column and hands back a `Report` you can turn into a data frame, count, or use to
substitute the fixable values.

`report` works with a plain list or with a pandas, polars, or pyarrow series. The
frame and the repaired column come back on the same backend you passed in.

## A quick pass over a column

```python
import biobouncer as bg

genes = ["TP53", "MLL", "notagene", None]
rep = bg.report(genes, "hgnc", how="cache")
rep
# <biobouncer report on 'hgnc' (cache mode): 1 valid, 1 repairable, 1 invalid, 1 missing of 4>
```

`MLL` is a withdrawn symbol, so it is invalid but repairable: its successor is
`KMT2A`. `notagene` is invalid with no fix. `None` is missing, not a failure.

## The verdict table

```python
rep.to_frame()
#       input  valid normalized suggestion
# 0      TP53   True       TP53        NaN
# 1       MLL  False        NaN      KMT2A
# 2  notagene  False        NaN        NaN
# 3       NaN   None        NaN        NaN
```

## Repair what you can

`repair` substitutes only the invalid-but-suggestable values. Valid values,
unmappable values, and missing values are left as they were, so the column keeps
its length and order.

```python
rep.repair()
# ['TP53', 'KMT2A', 'notagene', None]
```

With a dataframe, repair the column in place:

```python
import pandas as pd

df = pd.DataFrame({"gene": ["TP53", "MLL", "notagene"]})
df["gene"] = bg.report(df["gene"], "hgnc", how="cache").repair()
```

## Counts without a data frame

`report` never requires a data-frame library for the verdicts themselves. Pass a
list and read `.results` (a list of `Result`) or `.summary` (the counts):

```python
rep = bg.report(genes, "hgnc", how="cache")
rep.summary
# {'total': 4, 'valid': 1, 'invalid': 2, 'repairable': 1, 'missing': 1}
```

`to_frame` and repairing a native series use narwhals; install it with
`pip install "biobouncer[narwhals]"`.

## Report or enforce?

`report` is for inspecting and cleaning. To *enforce* validity inside a
framework (pandera, Great Expectations, pydantic, shiny), use the
[adapters](guide.md) instead: they raise or flag rather than hand you a table.
