# biogate

biogate validates biological identifiers and inputs. It answers one question,
"is this a valid identifier?", with the same verdict in Python and R. The R
package is documented [here](https://samuelbharti.github.io/biogate/r/).

## Install

```bash
pip install biogate

# development version from the monorepo subdirectory
pip install "git+https://github.com/samuelbharti/biogate.git#subdirectory=pkg-py"
```

The framework adapters (pandera, pydantic) are an optional extra:

```bash
pip install "biogate[adapters]"
```

## A first check

`pattern` mode is offline and deterministic. It checks the shape of an
identifier against the source's pattern. It does not check that the identifier
exists.

```python
import biogate as bg

bg.is_valid_id("MONDO:0005148", source_db="mondo")
# True

bg.is_valid_id(["P04637", "p04637"], source_db="uniprot")
# [True, False]
```

`is_valid_id` returns a single `bool` for a scalar input and a `list[bool]` for
a list. It preserves the order and length of the input.

## Rich results

`check_id` returns a list of `Result` records, one per input, in the same order.
Each record carries enough context to be self-describing: the verdict, the
canonical form of a valid input, and a best-effort correction for an invalid but
mappable one.

```python
for r in bg.check_id(["MONDO:0005148", "mondo:5148", "GO:0006915"], source_db="mondo"):
    print(r.input, r.valid, r.normalized, r.suggestion)
# MONDO:0005148 True  MONDO:0005148 None
# mondo:5148    False None          MONDO:0005148
# GO:0006915    False None          None
```

`mondo:5148` fails the pattern because of its lowercase prefix and short number,
but it is mappable, so `suggestion` holds the canonical form. `GO:0006915` is a
well-formed identifier from a different source, so it is invalid here with no
suggestion.

## What can be checked

`sources()` lists the source keys biogate knows about.

```python
bg.sources()
# ['bto', 'chebi', 'chembl', 'cl', 'clinvar', 'complexportal', ...]
```

Read on in the [guide](guide.md) for the checking modes, species and version
awareness, HGVS syntax, and the framework adapters, or jump to the
[API reference](reference.md).
