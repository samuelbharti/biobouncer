"""The result record returned for each checked identifier."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    """One verdict, with enough context to be self-describing.

    Attributes:
        input: The original value, unchanged.
        valid: Whether the input passed the check.
        normalized: Canonical form when valid, else None.
        suggestion: Best-effort correction when invalid but mappable, else None.
        source_db: The source the check ran against.
        version: Snapshot or release used. None for pattern mode.
        species: Species context, when applicable.
        how: The mode used ("pattern").
    """

    input: str
    valid: bool
    normalized: str | None
    suggestion: str | None
    source_db: str
    version: str | None
    species: str | None
    how: str
