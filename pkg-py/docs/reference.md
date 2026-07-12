# API reference

The public surface is small. `check_id` and `is_valid_id` are the entry points,
`sources` lists what can be checked, and the rest support cache mode and the
framework adapters.

## Checking identifiers

::: biogate.check_id

::: biogate.is_valid_id

::: biogate.Result

## Sources

::: biogate.sources

## Snapshots and cache

::: biogate.pull

::: biogate.snapshots

::: biogate.cache_dir

## Errors

Extrinsic modes raise rather than returning a silent `False`.

::: biogate.RemoteError

::: biogate.NoResolverError

::: biogate.MissingSnapshotError

::: biogate.MissingVersionError

::: biogate.NoBuilderError

## Framework adapters

The pandera and pydantic adapters install with `pip install "biogate[adapters]"`;
the narwhals adapter with `pip install "biogate[narwhals]"`.

::: biogate.checks.is_id

::: biogate.types.Id

::: biogate.narwhals.valid_id_mask
