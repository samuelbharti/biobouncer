"""WikiPathways remote mode: live existence checks via the published asset."""

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


def test_url_builds_the_asset_endpoint():
    from biobouncer._registry import get_source

    url = remote._wikipathways_url(get_source("wikipathways"), "WP554")
    assert url == (
        "https://www.wikipathways.org/wikipathways-assets/pathways/WP554/WP554.gpml"
    )


def test_existing_pathway_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("WP554", source_db="wikipathways", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "WP554"
    assert res.suggestion is None


def test_absent_pathway_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biobouncer.check_id("WP9999999", source_db="wikipathways", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biobouncer.check_id("wp554", source_db="wikipathways", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "WP554"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id("WPXYZ", source_db="wikipathways", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("WP554", source_db="wikipathways", how="remote")
    path = remote._remote_cache_path("wikipathways", "pathways", "WP554")
    assert not path.is_file()
