"""The single serialization point for a check result.

Both the R and Python packages read the field order and version from one vendored
description (``_data/schema/result.json``), so a serialized result has the same
shape in either language. The command-line JSON output and the DataFrame report
both go through here; nothing else should hand-build a result payload.

``schema_version`` labels the payload shape. Read it before the fields: it is
bumped whenever a field is added, removed, or renamed, so a consumer can tell one
shape from the next.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._result import Result

_SCHEMA = json.loads(
    (files("biobouncer") / "_data" / "schema" / "result.json").read_text(
        encoding="utf-8"
    )
)

SCHEMA_VERSION: str = _SCHEMA["schema_version"]
RESULT_FIELDS: tuple[str, ...] = tuple(_SCHEMA["result_fields"])
SUMMARY_FIELDS: tuple[str, ...] = tuple(_SCHEMA["summary_fields"])


def result_dict(result: Result) -> dict:
    """Serialize one ``Result`` to a plain dict, keys in the schema order."""
    return {field: getattr(result, field) for field in RESULT_FIELDS}


def summarize(results: Sequence[Result]) -> dict:
    """Count a batch of results into the shared summary fields.

    ``total`` is ``valid + invalid + missing + indeterminate``. ``repairable`` is
    the subset of ``invalid`` that carries a suggestion, so it is not added on top
    of the other counts. A ``valid is None`` result is ``indeterminate`` when it
    carries an ``error`` (a value that could not be checked) and ``missing``
    otherwise (an absent input).
    """
    total = len(results)
    valid = sum(1 for r in results if r.valid is True)
    invalid = sum(1 for r in results if r.valid is False)
    repairable = sum(
        1 for r in results if r.valid is False and r.suggestion is not None
    )
    indeterminate = sum(1 for r in results if r.valid is None and r.error is not None)
    missing = sum(1 for r in results if r.valid is None and r.error is None)
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "repairable": repairable,
        "missing": missing,
        "indeterminate": indeterminate,
    }


def payload(results: Sequence[Result]) -> dict:
    """Wrap a batch of results in the versioned envelope.

    The envelope is ``{"schema_version", "summary", "results"}``: the version
    first, then the counts over the whole batch, then one dict per result in
    input order.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "summary": summarize(results),
        "results": [result_dict(r) for r in results],
    }
