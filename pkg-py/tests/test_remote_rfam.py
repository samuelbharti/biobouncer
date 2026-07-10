"""Rfam remote mode: live existence checks via the Rfam API."""

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


def test_url_builds_the_rfam_family_endpoint():
    from biogate._registry import get_source

    url = remote._rfam_url(get_source("rfam"), "RF00001")
    assert url == "https://rfam.org/family/RF00001?content-type=application/json"


def test_existing_family_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("RF00001", source_db="rfam", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "RF00001"
    assert res.suggestion is None


def test_absent_family_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("RF99999", source_db="rfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("rf00001", source_db="rfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "RF00001"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("RF001", source_db="rfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("RF00001", source_db="rfam", how="remote")
    assert not remote._remote_cache_path("rfam", "family", "RF00001").is_file()
