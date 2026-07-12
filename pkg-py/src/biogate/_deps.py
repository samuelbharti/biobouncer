"""Friendly errors for the optional dependencies adapters and the report use."""

from __future__ import annotations


class MissingDependencyError(ImportError):
    """An optional dependency for an adapter or the report is not installed.

    It subclasses ``ImportError`` so existing ``except ImportError`` handlers
    still catch it, and it renders the exact ``pip install`` to run, naming the
    missing module and the extra that provides it.
    """

    def __init__(self, module: str, extra: str) -> None:
        self.module = module
        self.extra = extra
        super().__init__(
            f"The optional dependency {module!r} is required for this feature. "
            f"Install it with: pip install 'biogate[{extra}]'."
        )
