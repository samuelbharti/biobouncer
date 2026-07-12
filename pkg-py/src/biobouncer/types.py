"""pydantic integration: a validating string type for biological identifiers.

This module requires pydantic, an optional dependency. Install it with
``pip install biobouncer[adapters]``. The adapter never duplicates validation
logic; it calls :func:`biobouncer.is_valid_id`.

Example:
    >>> from pydantic import BaseModel
    >>> from biobouncer.types import Id
    >>> MondoId = Id("mondo")
    >>> class Row(BaseModel):
    ...     term: MondoId
    >>> Row(term="MONDO:0005148").term
    'MONDO:0005148'
"""

from __future__ import annotations

from typing import Annotated

from ._deps import MissingDependencyError

try:
    from pydantic import AfterValidator
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise MissingDependencyError("pydantic", "adapters") from exc

from .core import is_valid_id


def Id(source_db: str, how: str = "pattern", species=None, version=None):
    """Return a pydantic string type that validates a biological identifier.

    Use the returned type as a field annotation, most readably through an alias::

        MondoId = Id("mondo")


        class Row(BaseModel):
            term: MondoId

    A value that is not valid for ``source_db`` raises a pydantic
    ``ValidationError``.
    """

    def _check(value: str) -> str:
        if not is_valid_id(value, source_db, how=how, species=species, version=version):
            raise ValueError(f"{value!r} is not a valid {source_db} identifier")
        return value

    return Annotated[str, AfterValidator(_check)]
