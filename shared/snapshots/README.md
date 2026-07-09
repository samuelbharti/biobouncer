# shared/snapshots

Pinned snapshots of valid identifiers for `cache` mode. Each snapshot is a plain
text file of canonical identifiers, one per line, at
`snapshots/<source>/<version>.txt`.

The `sample` version bundled here is a small, curated subset of real identifiers.
It ships with the packages so that `cache` mode works offline and the tests are
deterministic. It is not the full identifier set for any source.

Full snapshots are produced by `biogate_pull()` (R) or `biogate.pull()` (Python)
and are written to the user cache directory, not committed here. `cache` mode
looks in the user cache directory first and falls back to a bundled snapshot.

An optional sidecar `snapshots/<source>/<version>.retired.tsv` maps a retired
identifier to its successor, one `retired<TAB>successor` pair per line (the
successor may be empty). In `cache` mode a well-formed id that is not in the
snapshot but is in this map is invalid, with the successor as its suggestion.

These files are vendored into each package by `python tools/sync_shared.py`. Do
not edit the vendored copies by hand.
