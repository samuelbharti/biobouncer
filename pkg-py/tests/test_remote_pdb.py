"""PDB remote mode: live existence checks via the RCSB PDB data API."""

import pytest

import biobouncer
import biobouncer._remote as remote
from biobouncer import RemoteError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _stub(status, body=None):
    def _http_get(url, timeout=30):
        return status, body

    return _http_get


def test_url_builds_the_rcsb_entry_endpoint():
    from biobouncer._registry import get_source

    url = remote._pdb_url(get_source("pdb"), "4HHB")
    assert url == "https://data.rcsb.org/rest/v1/core/entry/4HHB"


def test_existing_structure_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("4HHB", source_db="pdb", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "4HHB"
    assert res.suggestion is None


def test_absent_structure_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biobouncer.check_id("2ZZZ", source_db="pdb", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("4hhb", source_db="pdb", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "4HHB"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id("1ABCD", source_db="pdb", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("4HHB", source_db="pdb", how="remote")
    assert not remote._remote_cache_path("pdb", "entry", "4HHB").is_file()
