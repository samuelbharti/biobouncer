"""The result record returned for each checked identifier."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    """One verdict, with enough context to be self-describing.

    Attributes:
        input: The original value, or None for a missing input.
        valid: Whether the input passed the check, or None for a missing input.
        normalized: Canonical form when valid, else None.
        suggestion: Best-effort correction when invalid but mappable, else None.
        source_db: The source the check ran against.
        version: Snapshot or release used. None for pattern mode.
        species: Species context, when applicable.
        how: The checking mode used: "pattern", "cache", "remote", or
            "existence".
        error: Why the value could not be checked, else None. Set only for an
            indeterminate verdict (``valid is None`` with a non-None ``error``),
            which a remote failure under ``on_error="indeterminate"`` produces. A
            missing input is ``valid is None`` with ``error is None``.
    """

    input: str | None
    valid: bool | None
    normalized: str | None
    suggestion: str | None
    source_db: str
    version: str | None
    species: str | int | None
    how: str
    error: str | None = None
