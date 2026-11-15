# Variant identifiers

One variant can be written in several ways, and a check proves something
different for each of them. This page builds the common forms from VCF columns,
then checks them at three levels: the shape of the id, the reference sequence,
and the databases that record variants.

The running example is `rs7412`, a C to T change in the APOE gene on
chromosome 19.

## One variant, five written forms

| Form | `source_db` | Identifier | Genome build |
|---|---|---|---|
| gnomAD-style coordinate | `gnomad` | `19-44908822-C-T` | not stated |
| SPDI | `spdi` | `NC_000019.10:44908821:C:T` | GRCh38, through the sequence version |
| HGVS | `hgvs` | `NC_000019.10:g.44908822C>T` | GRCh38, through the sequence version |
| dbSNP | `dbsnp` | `rs7412` | none, a record id |
| ClinVar | `clinvar` | `VCV000017848` | none, a record id |

The first three describe the change itself, and you can build them from a VCF
row. The last two are record ids that a database assigned. The only way to
check them is a lookup.

## Three levels of checking

| Check | Source and mode | Network |
|---|---|---|
| The id is well formed | any variant source, `pattern` | no |
| The change fits the reference sequence | `hgvs`, `remote` | yes |
| The record id is current in its database | `dbsnp` or `clinvar`, `remote` | yes |

Each level is covered below, in this order.

## Build the coordinate forms from VCF columns

A VCF row gives a chromosome, a 1-based position, a reference allele, and an
alternate allele. For a single-base substitution, each coordinate form is those
four fields joined in a fixed order.

```python
import biobouncer as bg

rows = [
    {"chrom": "19", "pos": 44908822, "ref": "C", "alt": "T"},
    {"chrom": "19", "pos": 44908684, "ref": "T", "alt": "C"},
]

# The RefSeq accession of each chromosome, in the build the VCF was called on.
# NC_000019.10 is chromosome 19 in GRCh38.
refseq = {"19": "NC_000019.10"}

gnomad_ids = [f"{r['chrom']}-{r['pos']}-{r['ref']}-{r['alt']}" for r in rows]
spdi_ids = [
    f"{refseq[r['chrom']]}:{r['pos'] - 1}:{r['ref']}:{r['alt']}" for r in rows
]
hgvs_ids = [
    f"{refseq[r['chrom']]}:g.{r['pos']}{r['ref']}>{r['alt']}" for r in rows
]
# gnomad_ids -> ['19-44908822-C-T', '19-44908684-T-C']
# spdi_ids   -> ['NC_000019.10:44908821:C:T', 'NC_000019.10:44908683:T:C']
# hgvs_ids   -> ['NC_000019.10:g.44908822C>T', 'NC_000019.10:g.44908684T>C']
```

Two details differ between the forms. SPDI counts positions from 0, so its
position is the VCF position minus one. SPDI and HGVS also name a versioned
reference sequence, which fixes the genome build, while the gnomAD-style id
names only the chromosome.

The HGVS form above is correct for single-base substitutions only. HGVS writes
an insertion or a deletion with `ins`, `del`, `dup`, or `delins`, and the VCF
row carries an extra anchor base that HGVS leaves out. Convert those rows with
a variant normalizer first, then check the result here.

## Check the shape offline

`pattern` mode checks that an id is well formed. It needs no network and
suits a first pass over a whole column.

```python
ids = [
    "19-44908822-C-T",
    "chr19-44908822-c-t",
    "19-44908822--T",
    "19:44908822:C:T",
]
for r in bg.check_id(ids, source_db="gnomad"):
    print(r.input, r.valid, r.suggestion)
# 19-44908822-C-T True None
# chr19-44908822-c-t False chr19-44908822-C-T
# 19-44908822--T False None
# 19:44908822:C:T False None
```

A lowercase allele is repairable, so the second id gets a suggestion. An empty
allele and the wrong separator have no repair. `report(...).repair()` applies
every suggestion in one call and returns the other values unchanged.

```python
bg.report(ids, source_db="gnomad").repair()
# ['19-44908822-C-T', 'chr19-44908822-C-T', '19-44908822--T', '19:44908822:C:T']
```

## Limits of a shape check

A well-formed id can still describe a variant that does not fit the genome.
All three ids below pass. The second states G as the reference base where the
genome has C, and the third points past the end of the chromosome.

```python
bg.is_valid_id(
    ["19-44908822-C-T", "19-44908822-G-T", "19-999999999-C-T"],
    source_db="gnomad",
)
# [True, True, True]
```

The same holds for `spdi`, and for `hgvs` in `pattern` mode. A shape check
also cannot tell which genome build a gnomAD-style id counts on.

## Check a variant against the reference sequence

In `remote` mode, the `hgvs` source sends each well-formed description to the
Mutalyzer normalizer. Mutalyzer confirms that the reference sequence exists,
that the position lies inside it, and that the stated reference base is the
base found there. The lookup needs a network. The output below is from a run
on 2026-11-15.

```python
candidates = [
    "NC_000019.10:g.44908822C>T",   # the real variant
    "NC_000019.10:g.44908822G>T",   # wrong reference base
    "NC_000019.10:g.999999999C>T",  # past the end of the chromosome
]
for r in bg.check_id(candidates, source_db="hgvs", how="remote"):
    print(r.input, r.valid, r.version)
# NC_000019.10:g.44908822C>T True 2026-11-15T12:16:59Z
# NC_000019.10:g.44908822G>T False 2026-11-15T12:17:00Z
# NC_000019.10:g.999999999C>T False 2026-11-15T12:17:01Z
```

`version` holds the time of each lookup, because a live answer can change
later.

The `gnomad` and `spdi` sources have `pattern` mode only. To check one of
those ids against the reference, write the same change as HGVS, as in the
build step above, and check that.

A variant that fits the reference is a possible variant. This check does not
say that anyone has observed it, and no source looks a coordinate up in
gnomAD.

## Catch a coordinate from the wrong genome build

A gnomAD-style id does not say which build its position counts on. Writing
the variant as HGVS forces that choice, and the reference check then tests
it. `rs7412` sits at position 44908822 in GRCh38 and at 45412079 in GRCh37.

```python
bg.is_valid_id(
    [
        "NC_000019.10:g.44908822C>T",  # GRCh38 position on the GRCh38 sequence
        "NC_000019.9:g.44908822C>T",   # GRCh38 position on the GRCh37 sequence
        "NC_000019.9:g.45412079C>T",   # GRCh37 position on the GRCh37 sequence
    ],
    source_db="hgvs",
    how="remote",
)
# [True, False, True]
```

The mismatched pair fails because GRCh37 has an A at position 44908822, where
the id states a C.

A single passing id proves little about the build. A coordinate from the
wrong build still passes when the other build happens to carry the same base
at that position. Check a sample of rows, since each id is a separate
request. On the wrong build, many of them fail.

## Check a record id against its database

An rsID or a ClinVar accession carries no information about the change, so
its shape says little. `remote` mode looks the id up in the database that
assigned it.

```python
rsids = ["rs7412", "rs3200542", "rs999999999999"]
for r in bg.check_id(rsids, source_db="dbsnp", how="remote"):
    print(r.input, r.valid, r.suggestion)
# rs7412 True None
# rs3200542 False rs7412
# rs999999999999 False None
```

dbSNP merged `rs3200542` into `rs7412`. The old id is reported as not valid,
and the current id is suggested. An rsID that dbSNP never issued gets no
suggestion.

ClinVar accessions are checked the same way.

```python
bg.is_valid_id(
    ["VCV000017848", "VCV999999999"], source_db="clinvar", how="remote"
)
# [True, False]
```

A failed lookup raises `bg.RemoteError`. It never returns `False`, so a
network problem cannot be mistaken for a missing variant.
