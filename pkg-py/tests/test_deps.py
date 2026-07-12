"""Optional dependencies fail with an actionable install hint, not a raw error."""

import importlib
import sys

import pytest

import biobouncer
from biobouncer import MissingDependencyError


def test_error_is_an_importerror_with_the_install_command():
    err = MissingDependencyError("narwhals", "narwhals")
    assert isinstance(err, ImportError)
    assert err.module == "narwhals"
    assert err.extra == "narwhals"
    assert "pip install 'biobouncer[narwhals]'" in str(err)


def test_error_is_exported():
    assert biobouncer.MissingDependencyError is MissingDependencyError


class _Block:
    """A meta-path finder that makes one package look uninstalled."""

    def __init__(self, name):
        self.name = name

    def find_spec(self, name, path=None, target=None):
        if name == self.name or name.startswith(self.name + "."):
            raise ModuleNotFoundError(f"No module named {name!r}")
        return None


def test_adapter_import_without_its_dependency_is_friendly():
    # Importing the narwhals adapter with narwhals uninstalled raises the friendly
    # error, naming the extra to install, instead of a bare ModuleNotFoundError.
    import biobouncer.narwhals as nwmod

    dep = "narwhals"
    saved = {
        k: v
        for k, v in list(sys.modules.items())
        if k == dep or k.startswith(dep + ".")
    }
    for k in saved:
        del sys.modules[k]
    block = _Block(dep)
    sys.meta_path.insert(0, block)
    try:
        with pytest.raises(MissingDependencyError) as exc:
            importlib.reload(nwmod)
        assert "biobouncer[narwhals]" in str(exc.value)
    finally:
        sys.meta_path.remove(block)
        sys.modules.update(saved)
        importlib.reload(nwmod)  # restore a working module for the rest of the run
