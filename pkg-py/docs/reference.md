# API reference

The public surface is small. `check_id` and `is_valid_id` are the entry points,
`sources` lists what can be checked, and the rest support cache mode and the
framework adapters.

## Checking identifiers

::: biobouncer.check_id

::: biobouncer.is_valid_id

::: biobouncer.Result

## Cleaning a column

`report` is the recommended entry point for validating and repairing a whole
column. See the [report cookbook](report.md).

::: biobouncer.report

::: biobouncer.Report

## Generating test data

`synthesize` builds a labeled "messy column" of ids for a source (valid,
repairable, invalid, and missing), useful for exercising a validation pipeline or
`report` without hand-writing test data.

::: biobouncer.synthesize

## Sources

::: biobouncer.sources

## Snapshots and cache

::: biobouncer.pull

::: biobouncer.snapshots

::: biobouncer.cache_dir

## Errors

Extrinsic modes raise rather than returning a silent `False`.

::: biobouncer.RemoteError

::: biobouncer.NoResolverError

::: biobouncer.MissingSnapshotError

::: biobouncer.MissingVersionError

::: biobouncer.NoBuilderError

::: biobouncer.MissingDependencyError

## Framework adapters

The pandera and pydantic adapters install with `pip install "biobouncer[adapters]"`;
the narwhals adapter with `pip install "biobouncer[narwhals]"`.

::: biobouncer.checks.is_id

::: biobouncer.types.Id

::: biobouncer.narwhals.valid_id_mask
