import biogate


def test_package_has_version():
    assert isinstance(biogate.__version__, str)
    assert biogate.__version__
