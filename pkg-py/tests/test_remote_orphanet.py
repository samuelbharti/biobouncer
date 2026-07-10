"""Orphanet remote mode: OLS lookup against ordo with an id-prefix rewrite."""

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


def _found():
    return {"page": {"totalElements": 1}}


def test_url_rewrites_the_orpha_prefix_for_ols():
    from biogate._registry import get_source

    url = remote._ols_url(get_source("orphanet"), "ORPHA:558")
    assert url == (
        "https://www.ebi.ac.uk/ols4/api/ontologies/ordo/terms?obo_id=Orphanet:558"
    )


def test_existing_term_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _found()))
    res = biogate.check_id("ORPHA:558", source_db="orphanet", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "ORPHA:558"
    assert res.suggestion is None


def test_absent_term_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("ORPHA:999999", source_db="orphanet", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _found()))
    res = biogate.check_id("orpha:558", source_db="orphanet", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "ORPHA:558"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("ORPHA558", source_db="orphanet", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("ORPHA:558", source_db="orphanet", how="remote")
    path = remote._remote_cache_path("ols", "ordo", "ORPHA:558")
    assert not path.is_file()
