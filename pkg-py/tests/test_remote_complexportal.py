"""Complex Portal remote mode: live existence checks via the EBI web service."""

import pytest

import biogate
import biogate._remote as remote
from biogate import RemoteError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def _stub(status, body=None):
    def _http_get(url, timeout=30):
        return status, body

    return _http_get


def test_url_builds_the_complex_endpoint():
    from biogate._registry import get_source

    url = remote._complexportal_url(get_source("complexportal"), "CPX-2158")
    assert url == "https://www.ebi.ac.uk/intact/complex-ws/complex/CPX-2158"


def test_existing_complex_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("CPX-2158", source_db="complexportal", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "CPX-2158"
    assert res.suggestion is None


def test_absent_complex_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("CPX-9999999", source_db="complexportal", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("cpx-2158", source_db="complexportal", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "CPX-2158"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("CPX-XYZ", source_db="complexportal", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("CPX-2158", source_db="complexportal", how="remote")
    path = remote._remote_cache_path("complexportal", "complex", "CPX-2158")
    assert not path.is_file()
