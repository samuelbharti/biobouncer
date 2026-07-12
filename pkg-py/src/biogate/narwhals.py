"""narwhals integration: validate a column of identifiers in any dataframe.

This module requires narwhals, an optional dependency. Install it with
``pip install biogate[narwhals]``. narwhals is a thin, dataframe-agnostic layer,
so one check covers pandas, polars, and pyarrow alike. The adapter never
duplicates validation logic; it calls :func:`biogate.is_valid_id`.

Example:
    >>> import polars as pl
    >>> from biogate.narwhals import valid_id_mask
    >>> s = pl.Series("term", ["MONDO:0005148", "mondo:5148"])
    >>> valid_id_mask(s, "mondo").to_list()
    [True, False]
"""

from __future__ import annotations

from ._deps import MissingDependencyError

try:
    import narwhals as nw
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise MissingDependencyError("narwhals", "narwhals") from exc

from .core import is_valid_id


def valid_id_mask(column, source_db, how="pattern", species=None, version=None):
    """Return a boolean mask over a column: ``False`` marks an invalid id.

    ``column`` is a native series from any narwhals-supported backend (pandas,
    polars, or pyarrow); the result is a native boolean series of the same
    backend. A value is ``False`` only when it is a malformed or non-existent
    identifier. A missing cell is ``True``, because a missing value is not a
    failed identifier (mirroring how the pandera adapter leaves null cells to
    column nullability). So ``~mask`` selects the rows that fail an id check, and
    ``mask.all()`` is true when nothing fails.
    """
    series = nw.from_native(column, series_only=True)
    verdicts = is_valid_id(
        series.to_list(), source_db, how=how, species=species, version=version
    )
    passes = [verdict is not False for verdict in verdicts]
    mask = nw.new_series(
        name=series.name or "valid_id",
        values=passes,
        dtype=nw.Boolean(),
        backend=nw.get_native_namespace(series),
    )
    return mask.to_native()
