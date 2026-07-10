"""InterPro remote mode: live existence checks via the EBI InterPro API."""

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


def test_url_builds_the_interpro_entry_endpoint():
    from biogate._registry import get_source

    url = remote._interpro_url(get_source("interpro"), "IPR000001")
    assert url == "https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR000001"


def test_existing_entry_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("IPR000001", source_db="interpro", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "IPR000001"
    assert res.suggestion is None


def test_absent_entry_is_invalid(monkeypatch):
    # The InterPro entry endpoint answers 204 for a well-formed but absent id.
    monkeypatch.setattr(remote, "_http_get", _stub(204))
    res = biogate.check_id("IPR999999", source_db="interpro", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("ipr000001", source_db="interpro", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "IPR000001"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("IPRABCDEF", source_db="interpro", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("IPR000001", source_db="interpro", how="remote")
    path = remote._remote_cache_path("interpro", "interpro", "IPR000001")
    assert not path.is_file()
