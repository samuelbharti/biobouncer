"""Reactome remote mode: live existence checks via the Reactome content service."""

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


def test_url_builds_the_content_service_query_endpoint():
    from biogate._registry import get_source

    url = remote._reactome_url(get_source("reactome"), "R-HSA-68886")
    assert url == "https://reactome.org/ContentService/data/query/R-HSA-68886"


def test_existing_stable_id_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("R-HSA-68886", source_db="reactome", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "R-HSA-68886"
    assert res.suggestion is None


def test_absent_stable_id_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("R-HSA-99999999", source_db="reactome", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("r-hsa-68886", source_db="reactome", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "R-HSA-68886"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("R-HSA-XYZ", source_db="reactome", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("R-HSA-68886", source_db="reactome", how="remote")
    path = remote._remote_cache_path("reactome", "query", "R-HSA-68886")
    assert not path.is_file()
