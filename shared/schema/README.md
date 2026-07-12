# Result schema

`result.json` is the single, language-neutral description of a serialized
`check_id` result. Both packages read it from their vendored copy so the R and
Python serializations cannot drift.

- `schema_version` labels the payload shape. Bump it when a field is added,
  removed, or renamed. Consumers read the version before the fields.
- `result_fields` is the order of keys in one serialized result. `error` carries
  the reason a value could not be checked; it is set only for an indeterminate
  verdict (`valid` null with a non-null `error`), which a network failure under
  `on_error = "indeterminate"` produces.
- `summary_fields` is the set of counts a report summary reports. `repairable`
  is a subset of `invalid`; `total` is `valid + invalid + missing +
  indeterminate`.

This file is vendored into `pkg-r/inst/extdata/schema/` and
`pkg-py/src/biobouncer/_data/schema/` by `tools/sync_shared.py`. Edit it here, never
in a vendored copy.
