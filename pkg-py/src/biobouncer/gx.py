"""Great Expectations integration: a column-map expectation for identifiers.

This module requires Great Expectations, an optional dependency. Install it with
``pip install "biobouncer[gx]"``. The adapter never duplicates validation logic; it
calls :func:`biobouncer.is_valid_id`.

Example:
    >>> import pandas as pd
    >>> import great_expectations as gx
    >>> from biobouncer.gx import ExpectColumnValuesToBeValidId
    >>> context = gx.get_context(mode="ephemeral")
    >>> df = pd.DataFrame({"term": ["MONDO:0005148", "MONDO:0018076"]})
    >>> batch = (
    ...     context.data_sources.add_pandas("p")
    ...     .add_dataframe_asset("a")
    ...     .add_batch_definition_whole_dataframe("b")
    ...     .get_batch(batch_parameters={"dataframe": df})
    ... )
    >>> batch.validate(
    ...     ExpectColumnValuesToBeValidId(column="term", source_db="mondo")
    ... ).success
    True

``version`` is not exposed as an expectation argument because it collides with a
reserved Great Expectations field. Pin a version by validating a snapshot with
the core API before handing the frame to Great Expectations.
"""

from __future__ import annotations

from typing import Optional

from ._deps import MissingDependencyError

try:
    import pandas as pd
    from great_expectations.execution_engine import PandasExecutionEngine
    from great_expectations.expectations.expectation import ColumnMapExpectation
    from great_expectations.expectations.metrics.map_metric_provider import (
        ColumnMapMetricProvider,
        column_condition_partial,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise MissingDependencyError("great_expectations", "gx") from exc

from .core import is_valid_id


class ColumnValuesBiobouncerValid(ColumnMapMetricProvider):
    """Column-map metric: is each value a valid identifier for the source?"""

    condition_metric_name = "column_values.biobouncer_valid"
    condition_value_keys = ("source_db", "how", "species")

    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(cls, column, source_db, how="pattern", species=None, **kwargs):  # noqa: N805
        verdicts = is_valid_id(
            list(column), source_db=source_db, how=how, species=species
        )
        return pd.Series(verdicts, index=column.index)


class ExpectColumnValuesToBeValidId(ColumnMapExpectation):
    """Expect each value in a column to be a valid identifier for a source.

    Configure it with ``source_db`` (the source key, for example ``"mondo"``) and
    ``how`` (the checking mode: ``"pattern"`` and ``"cache"`` are offline while
    ``"remote"`` checks live existence), plus an optional ``species`` for
    species-aware sources and the usual Great Expectations ``mostly`` tolerance, a
    fraction in [0, 1].
    """

    map_metric = "column_values.biobouncer_valid"
    success_keys = ("source_db", "how", "species", "mostly")

    source_db: str
    how: str = "pattern"
    # Optional[...] not "str | None": Great Expectations resolves these field
    # annotations at runtime through pydantic v1, which fails on Python 3.9.
    species: Optional[str] = None  # noqa: UP045
