"""Pfam remote mode: live existence checks via the EBI InterPro API."""

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


def test_url_builds_the_pfam_entry_endpoint():
    from biobouncer._registry import get_source

    url = remote._interpro_url(get_source("pfam"), "PF00001")
    assert url == "https://www.ebi.ac.uk/interpro/api/entry/pfam/PF00001"


def test_existing_family_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("PF00001", source_db="pfam", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "PF00001"
    assert res.suggestion is None


def test_absent_family_is_invalid(monkeypatch):
    # The InterPro entry endpoint answers 204 for a well-formed but absent id.
    monkeypatch.setattr(remote, "_http_get", _stub(204))
    res = biobouncer.check_id("PF99999", source_db="pfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("pf00001", source_db="pfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "PF00001"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id("PFABCDE", source_db="pfam", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("PF00001", source_db="pfam", how="remote")
    path = remote._remote_cache_path("interpro", "pfam", "PF00001")
    assert not path.is_file()
