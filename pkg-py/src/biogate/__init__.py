"""biogate: validate biological identifiers and inputs.

The public surface is small: ``check_id`` and ``is_valid_id``, plus ``sources``
to list what can be checked. Offline ``pattern`` and ``cache`` modes are
implemented; ``cache`` mode looks up existence in a pinned snapshot.
"""

from __future__ import annotations

from ._cache import MissingSnapshotError, MissingVersionError, cache_dir, snapshots
from ._registry import sources
from ._result import Result
from .core import check_id, is_valid_id

__version__ = "0.1.0.dev0"

__all__ = [
    "MissingSnapshotError",
    "MissingVersionError",
    "Result",
    "cache_dir",
    "check_id",
    "is_valid_id",
    "snapshots",
    "sources",
    "__version__",
]
