"""PROSITE remote mode: live existence checks via the ExPASy entry endpoint."""

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


def test_url_builds_the_expasy_entry_endpoint():
    from biogate._registry import get_source

    url = remote._prosite_url(get_source("prosite"), "PS00001")
    assert url == "https://prosite.expasy.org/PS00001"


def test_existing_pattern_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("PS00001", source_db="prosite", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "PS00001"
    assert res.suggestion is None


def test_existing_profile_is_valid(monkeypatch):
    # One ExPASy endpoint serves both entry types, so a profile validates too.
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("PS50011", source_db="prosite", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "PS50011"


def test_absent_entry_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("PS99999", source_db="prosite", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("ps00001", source_db="prosite", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "PS00001"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("PS001", source_db="prosite", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("PS00001", source_db="prosite", how="remote")
    assert not remote._remote_cache_path("prosite", "entry", "PS00001").is_file()
