# Command line

Installing the Python package puts a `biogate` command on your path. It
validates identifiers from arguments, files, or standard input, and exits
non-zero when any input is invalid, so it drops straight into shell pipelines
and CI checks.

```bash
pip install biogate
biogate --version
```

## Check identifiers

```console
$ biogate check --source mondo MONDO:0005148 mondo:5148 GO:0006915
ok    MONDO:0005148
FAIL  mondo:5148  did you mean MONDO:0005148?
FAIL  GO:0006915
```

The exit code is `0` when every input is valid, `1` when any input is invalid,
and `2` on a usage error such as an unknown source. That makes it usable as a
gate:

```bash
biogate check --source mondo --file ids.txt || echo "some ids are invalid"
```

Read from a file (one id per line, blank lines ignored) or from a pipe:

```bash
biogate check --source mondo --file ids.txt
cat ids.txt | biogate check --source mondo
```

Pick the checking mode and, where it applies, a species or version:

```bash
biogate check --source ensembl --how remote --species homo_sapiens ENSG00000139618
```

## Output formats

`--format text` (the default) is human-readable. `--format tsv` and
`--format json` are for scripts. Add `--quiet` to drop the summary line, and
`--invalid-only` to print only the failures.

```console
$ biogate check --source uniprot --format tsv -q P04637 p04637
input   valid   normalized      suggestion
P04637  true    P04637
p04637  false           P04637
```

```bash
biogate check --source mondo --format json mondo:5148 | jq '.[0].suggestion'
# "MONDO:0005148"
```

## Discover sources

`biogate sources` lists the keys, and `biogate info` shows a valid example and
the supported modes for each, so you never have to guess.

```console
$ biogate info --source mondo
key     name                    example         modes                   species_aware
mondo   MONDO Disease Ontology  MONDO:0005148   pattern,cache,remote    false
```

See the [sources cookbook](sources.md) for the full list.
