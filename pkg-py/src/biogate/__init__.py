"""biogate: validate biological identifiers and inputs.

The public surface is small: ``check_id`` and ``is_valid_id``, plus ``sources``
to list what can be checked. Offline ``pattern`` and ``cache`` modes and live
``remote`` mode are implemented, along with ``existence`` mode, which uses a
snapshot when one is available and otherwise falls back to ``remote``.
``cache`` looks up existence in a pinned snapshot; ``remote`` looks it up
against the source API.
"""

from __future__ import annotations

from ._cache import (
    MissingSnapshotError,
    MissingVersionError,
    NoBuilderError,
    cache_dir,
    pull,
    snapshots,
)
from ._registry import UnknownSourceError, source_info, sources
from ._remote import NoResolverError, RemoteError
from ._result import Result
from .core import InvalidModeError, check_id, is_valid_id
from .schema import SCHEMA_VERSION

__version__ = "0.1.0"

__all__ = [
    "SCHEMA_VERSION",
    "InvalidModeError",
    "MissingSnapshotError",
    "MissingVersionError",
    "NoBuilderError",
    "NoResolverError",
    "RemoteError",
    "Result",
    "UnknownSourceError",
    "cache_dir",
    "check_id",
    "is_valid_id",
    "pull",
    "snapshots",
    "source_info",
    "sources",
    "__version__",
]
