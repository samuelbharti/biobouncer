"""biobouncer: validate biological identifiers and inputs.

The public surface is small: ``check_id`` and ``is_valid_id``, plus ``sources``
to list what can be checked. Offline ``pattern`` and ``cache`` modes and live
``remote`` mode are implemented, along with ``existence`` mode, which uses a
snapshot when one is available and otherwise falls back to ``remote``.
``cache`` looks up existence in a pinned snapshot; ``remote`` looks it up
against the source API.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ._cache import (
    MissingSnapshotError,
    MissingVersionError,
    NoBuilderError,
    cache_dir,
    pull,
    snapshots,
)
from ._deps import MissingDependencyError
from ._registry import UnknownSourceError, source_info, sources
from ._remote import NoResolverError, RemoteError
from ._result import Result
from .core import InvalidModeError, check_id, is_valid_id
from .report import Report, report
from .schema import SCHEMA_VERSION
from .synthetic import synthesize

# Single-sourced from the package metadata (pyproject.toml), so the version is
# declared in exactly one place.
try:
    __version__ = version("biobouncer")
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled tree
    __version__ = "0.0.0+unknown"

__all__ = [
    "SCHEMA_VERSION",
    "InvalidModeError",
    "MissingDependencyError",
    "MissingSnapshotError",
    "MissingVersionError",
    "NoBuilderError",
    "NoResolverError",
    "RemoteError",
    "Report",
    "Result",
    "UnknownSourceError",
    "cache_dir",
    "check_id",
    "is_valid_id",
    "pull",
    "report",
    "snapshots",
    "source_info",
    "sources",
    "synthesize",
    "__version__",
]
