"""pandera integration: a Check for validating a column of identifiers.

This module requires pandera, an optional dependency. Install it with
``pip install biobouncer[adapters]``. The adapter never duplicates validation
logic; it calls :func:`biobouncer.is_valid_id`.

Example:
    >>> import pandas as pd
    >>> import pandera.pandas as pa
    >>> from biobouncer.checks import is_id
    >>> schema = pa.DataFrameSchema({"term": pa.Column(str, is_id("mondo"))})
    >>> df = pd.DataFrame({"term": ["MONDO:0005148", "MONDO:0018076"]})
    >>> list(schema.validate(df)["term"])
    ['MONDO:0005148', 'MONDO:0018076']
"""

from __future__ import annotations

from ._deps import MissingDependencyError

try:
    import pandas as pd

    try:  # pandera >= 0.20 moved the pandas backend under its own namespace.
        from pandera.pandas import Check
    except ImportError:  # pragma: no cover - older pandera
        from pandera import Check
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise MissingDependencyError("pandera", "adapters") from exc

from .core import is_valid_id


def is_id(source_db: str, how: str = "pattern", species=None, version=None, **kwargs):
    """Return a pandera ``Check`` that validates a column of identifiers.

    Use it as a column check in a schema::

        schema = pa.DataFrameSchema({"term": pa.Column(str, is_id("mondo"))})

    The check is vectorized: it hands the whole column to
    :func:`biobouncer.is_valid_id` and flags each value that is not valid for
    ``source_db``. Any extra keyword arguments are passed through to
    ``pandera.Check`` (for example ``name`` or ``raise_warning``).
    """

    def _check(series: pd.Series) -> pd.Series:
        verdicts = is_valid_id(
            list(series), source_db, how=how, species=species, version=version
        )
        return pd.Series(verdicts, index=series.index)

    kwargs.setdefault("error", f"value is not a valid {source_db} identifier")
    return Check(_check, **kwargs)
