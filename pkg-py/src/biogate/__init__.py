"""biogate: validate biological identifiers and inputs.

The public surface is small: ``check_id`` and ``is_valid_id``, plus ``sources``
to list what can be checked. Offline ``pattern`` and ``cache`` modes and live
``remote`` mode are implemented. ``cache`` looks up existence in a pinned
snapshot; ``remote`` looks it up against the source API.
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
from ._registry import sources
from ._remote import NoResolverError, RemoteError
from ._result import Result
from .core import check_id, is_valid_id

__version__ = "0.1.0.dev0"

__all__ = [
    "MissingSnapshotError",
    "MissingVersionError",
    "NoBuilderError",
    "NoResolverError",
    "RemoteError",
    "Result",
    "cache_dir",
    "check_id",
    "is_valid_id",
    "pull",
    "snapshots",
    "sources",
    "__version__",
]
