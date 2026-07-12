import biobouncer


def test_package_has_version():
    assert isinstance(biobouncer.__version__, str)
    assert biobouncer.__version__
