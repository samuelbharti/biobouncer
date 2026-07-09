"""biogate: validate biological identifiers and inputs.

The public surface is small: ``check_id`` and ``is_valid_id``, plus ``sources``
to list what can be checked. Only offline ``pattern`` mode is implemented so far.
"""

from __future__ import annotations

from ._registry import sources
from ._result import Result
from .core import check_id, is_valid_id

__version__ = "0.1.0.dev0"

__all__ = ["Result", "check_id", "is_valid_id", "sources", "__version__"]
