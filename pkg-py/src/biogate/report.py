"""Validate a whole column, then report or repair it in one call.

``report()`` is the recommended entry point for the "clean my column" job. It runs
:func:`check_id` over a column and returns a :class:`Report` you can turn into a
data frame, count, or use to substitute the fixable values. It builds on narwhals,
so the frame it returns is pandas, polars, or pyarrow to match the column you
passed. Pure-Python callers can pass a list and read ``Report.results`` with no
data-frame dependency at all.

For enforcing validity inside a framework (pandera, Great Expectations, pydantic,
shiny), reach for the adapters instead; ``report`` is for inspecting and cleaning.
"""

from __future__ import annotations

from ._deps import MissingDependencyError
from ._result import Result
from .core import check_id
from .schema import summarize

# The per-row columns of the report frame: the result fields that vary within one
# column checked against one source (source_db, version, species, how are
# constant, so they live on the Report, not in every row).
_FRAME_COLUMNS = ("input", "valid", "normalized", "suggestion")


def _require_narwhals():
    try:
        import narwhals as nw
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise MissingDependencyError("narwhals", "narwhals") from exc
    return nw


def _read_column(column) -> tuple[list, object, str]:
    """Return ``(values, backend, name)`` for a column.

    A plain list or tuple stays pure Python, with ``backend`` ``None``. Any other
    object is read through narwhals as a native series, so the report can rebuild
    a frame or series on the same backend (pandas, polars, or pyarrow).
    """
    if isinstance(column, (list, tuple)):
        return list(column), None, "input"
    nw = _require_narwhals()
    try:
        series = nw.from_native(column, series_only=True)
    except TypeError:
        # Not a native series narwhals recognizes; treat it as a plain iterable.
        return list(column), None, "input"
    return series.to_list(), nw.get_native_namespace(series), series.name or "input"


def _repaired_value(result: Result):
    """The repaired value for one result.

    Substitute only an invalid value that has a suggestion. A valid value, an
    invalid value with no suggestion, and a missing value are all left untouched.
    """
    if result.valid is False and result.suggestion is not None:
        return result.suggestion
    return result.input


class Report:
    """The outcome of checking a whole column, ready to inspect or repair.

    Attributes:
        results: One :class:`Result` per input, in order. Always available, with
            no data-frame dependency.
        source_db: The source the column was checked against.
        how: The checking mode used.
    """

    def __init__(self, results, source_db, how, backend=None, name="input"):
        self.results = results
        self.source_db = source_db
        self.how = how
        self._backend = backend
        self._name = name

    def __len__(self) -> int:
        return len(self.results)

    @property
    def summary(self) -> dict:
        """Counts over the column: total, valid, invalid, repairable, missing."""
        return summarize(self.results)

    def to_frame(self, backend=None):
        """Return a native data frame of the per-row verdicts.

        The frame has the columns ``input``, ``valid``, ``normalized``, and
        ``suggestion``. It comes back on the same backend as the column passed to
        ``report`` (pandas, polars, or pyarrow); a report built from a plain list
        defaults to pandas. Pass ``backend`` to force one. Requires narwhals.
        """
        nw = _require_narwhals()
        target = backend if backend is not None else self._backend
        if target is None:
            target = "pandas"
        data = {
            column: [getattr(r, column) for r in self.results]
            for column in _FRAME_COLUMNS
        }
        return nw.from_dict(data, backend=target).to_native()

    def repair(self):
        """Return the column with every fixable value substituted.

        An invalid value that has a suggestion is replaced by that suggestion.
        Valid values, invalid values with no suggestion, and missing values are
        left as they were, so the result is the same length and order as the
        input. A report built from a native series returns a native series on the
        same backend; one built from a list returns a list.
        """
        repaired = [_repaired_value(r) for r in self.results]
        if self._backend is None:
            return repaired
        nw = _require_narwhals()
        return nw.new_series(self._name, repaired, backend=self._backend).to_native()

    def __repr__(self) -> str:
        counts = self.summary
        unmappable = counts["invalid"] - counts["repairable"]
        return (
            f"<biogate report on {self.source_db!r} ({self.how} mode): "
            f"{counts['valid']} valid, {counts['repairable']} repairable, "
            f"{unmappable} invalid, {counts['missing']} missing "
            f"of {counts['total']}>"
        )


def report(
    column,
    source_db: str,
    how: str = "pattern",
    species: str | None = None,
    version: str | None = None,
    refresh: bool = False,
) -> Report:
    """Check a whole column and return a :class:`Report`.

    Args:
        column: A list of ids, or a pandas, polars, or pyarrow series.
        source_db: Source key, for example ``"hgnc"``. See ``sources()``.
        how: Checking mode, as in :func:`check_id`.
        species: Optional species context.
        version: Optional version context. In cache mode it defaults to the
            latest installed snapshot.
        refresh: In remote checks, skip any cached response and refetch.

    Returns:
        A :class:`Report`. Use ``.to_frame()`` for a data frame of verdicts,
        ``.repair()`` to substitute the fixable values, ``.summary`` for counts,
        or ``.results`` for the raw list.
    """
    values, backend, name = _read_column(column)
    results = check_id(
        values,
        source_db,
        how=how,
        species=species,
        version=version,
        refresh=refresh,
    )
    return Report(results, source_db=source_db, how=how, backend=backend, name=name)
