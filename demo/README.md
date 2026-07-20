# biobouncer demo

Two notebooks that run the same story through
[biobouncer](https://github.com/samuelbharti/biobouncer) in Python and in R, over
the same messy data, so you can see the two packages return the same answers.

Both notebooks follow the same seven steps:

1. **Discover**: `sources()` (46 databases) and `source_info()`
2. **Snapshots**: the bundled offline data (`snapshots()`, `cache_dir()`)
3. **`pattern` mode**: is the string well-formed? (offline)
4. **`cache` mode**: does the id exist? repair renamed and obsolete ids (offline)
5. **`pattern` across many sources**: UniProt, Ensembl, RefSeq, dbSNP, HGVS, ChEBI
6. **`remote` mode**: a live API check, species aware (needs a network, skips
   cleanly without one)
7. **Framework integration**: pandera and pydantic in Python, checkmate and
   assertr in R

## Files

```text
demo/
├── biobouncer_python.ipynb   # Python notebook
├── biobouncer_r.ipynb        # R notebook
├── data/
│   ├── associations.csv      # messy gene / disease / process table
│   └── identifiers.csv       # mixed accessions across databases
└── pyproject.toml            # Python dependencies for the demo
```

The data is deliberately messy: retired gene symbols (`MLL` is now `KMT2A`,
`CARS` is now `CARS1`), an obsolete GO term (`GO:0006917` is now `GO:0006915`), a
mis-cased id (`mondo:5148`), an id that does not exist, and a missing value. Every
validation mode has something to find.

## Run it

Each notebook's first cell installs biobouncer, so opening the notebook and
running all cells is enough. The cell is safe to re-run.

For the Python notebook, this directory is a uv project:

```sh
cd demo
uv run jupyter lab
```

For the R notebook you need Jupyter with
[IRkernel](https://irkernel.github.io/installation/), or you can open it in any
environment that runs R notebooks. The notebooks name the stock `python3` and
`ir` kernels, so they should open without any per-machine setup.

`remote` mode reaches live APIs. Those cells are wrapped in `try`/`except` in
Python and `tryCatch` in R, so the notebooks run offline too. The other three
modes never touch the network.

## These notebooks are tested

`.github/workflows/demo.yml` runs both notebooks against the current checkout on
every pull request that touches the packages, the shared spec, or the demo
itself. The install cell is skipped there so CI exercises the code in the
repository rather than the last release. If a change breaks the demo, the pull
request fails.

To run the same checks yourself, from the repository root:

```sh
python tools/run_demo.py python   # execute the Python notebook
python tools/run_demo.py r        # run the R notebook's code through Rscript
```

Add `--save` to the Python command to write the executed outputs back into the
notebook, which is how the stored outputs are kept current with the package.
