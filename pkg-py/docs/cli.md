# Command line

Installing the Python package puts a `biobouncer` command on your path. It
validates identifiers from arguments, files, or standard input, and exits
non-zero when any input is invalid, so it drops straight into shell pipelines
and CI checks.

```bash
pip install biobouncer
biobouncer --version
```

## Check identifiers

```console
$ biobouncer check --source mondo MONDO:0005148 mondo:5148 GO:0006915
ok    MONDO:0005148
FAIL  mondo:5148  did you mean MONDO:0005148?
FAIL  GO:0006915
```

The exit code is `0` when every input is valid, `1` when any input is invalid,
`2` on a usage error such as an unknown source, and `3` when a remote check
cannot reach the source API. A remote id that cannot be checked does not sink the
whole run: it prints as `ERR` with the reason, the ids that could be checked
still print their verdicts, and the run exits `3`. That makes it usable as a gate:

```bash
biobouncer check --source mondo --file ids.txt || echo "some ids are invalid"
```

Read from a file (one id per line, blank lines ignored) or from a pipe:

```bash
biobouncer check --source mondo --file ids.txt
cat ids.txt | biobouncer check --source mondo
```

Pick the checking mode and, where it applies, a species or version:

```bash
biobouncer check --source ensembl --how remote --species homo_sapiens ENSG00000139618
```

Remote checks cache each answer. Add `--refresh` to skip the cache and look the
id up live again.

## Output formats

`--format text` (the default) is human-readable. `--format tsv` and
`--format json` are for scripts. Add `--quiet` to drop the summary line, and
`--invalid-only` to print only the failures.

```console
$ biobouncer check --source uniprot --format tsv -q P04637 p04637
input   valid   normalized      suggestion      error
P04637  true    P04637
p04637  false           P04637
```

The `error` column and, in the JSON output, an `indeterminate` count carry the
ids a remote check could not reach.

The JSON output is a versioned envelope: a `schema_version`, a `summary` with the
counts over the whole batch, and a `results` list with one object per id carrying
every field, including `version` and `species`.

```bash
biobouncer check --source mondo --format json mondo:5148 | jq '.results[0].suggestion'
# "MONDO:0005148"
```

## Discover sources

`biobouncer sources` lists the keys, and `biobouncer info` shows a valid example and
the supported modes for each, so you never have to guess.

```console
$ biobouncer info --source mondo
key     name                    example         modes                   species_aware
mondo   MONDO Disease Ontology  MONDO:0005148   pattern,cache,remote    false
```

See the [sources cookbook](sources.md) for the full list.

## Cache snapshots

Cache mode checks an id against a pinned local snapshot. `biobouncer snapshots`
lists the snapshots you have, both the small bundled samples and any you have
downloaded, and prints the cache directory they live in.

```console
$ biobouncer snapshots
cache dir: /home/you/.cache/biobouncer
source  version  n_ids  location
mondo   sample   6      bundled
```

`biobouncer pull --source mondo` downloads a full snapshot for a source that has a
builder (the OBO ontologies, or `hgnc` via its complete-set TSV) and writes it to
the cache directory. A source with no builder, such as `ensembl`, exits `2`.
