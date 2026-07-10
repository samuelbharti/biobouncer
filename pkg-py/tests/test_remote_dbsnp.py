"""dbSNP remote mode: existence and merge handling via the NCBI RefSNP API."""

import pytest

import biogate
import biogate._remote as remote
from biogate import RemoteError

_MERGED = {"merged_snapshot_data": {"merged_into": ["7412"]}}


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def _stub(status, body=None):
    def _http_get(url, timeout=30):
        return status, body

    return _http_get


def test_url_strips_the_rs_prefix():
    from biogate._registry import get_source

    url = remote._dbsnp_url(get_source("dbsnp"), "rs7412")
    assert url.endswith("/refsnp/7412")


def test_current_rsid_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200))
    res = biogate.check_id("rs7412", source_db="dbsnp", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "rs7412"
    assert res.suggestion is None


def test_merged_rsid_is_invalid_and_suggests_primary(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _MERGED))
    res = biogate.check_id("rs3200542", source_db="dbsnp", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "rs7412"


def test_absent_rsid_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(404))
    res = biogate.check_id("rs999999999999", source_db="dbsnp", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("ss12345", source_db="dbsnp", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("rs7412", source_db="dbsnp", how="remote")
    assert not remote._remote_cache_path("dbsnp", "refsnp", "rs7412").is_file()


def test_merge_round_trips_through_the_cache(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _MERGED))
    assert (
        biogate.check_id("rs3200542", source_db="dbsnp", how="remote")[0].suggestion
        == "rs7412"
    )

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert (
        biogate.check_id("rs3200542", source_db="dbsnp", how="remote")[0].suggestion
        == "rs7412"
    )
