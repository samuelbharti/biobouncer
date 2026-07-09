"""Remote mode behavior, fully offline by monkeypatching the network seam."""

import json

import pytest

import biogate
import biogate._remote as remote
from biogate import NoResolverError, RemoteError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def _stub_present(present):
    """Return a _http_get stub where only ids in ``present`` exist."""

    def _http_get(url, timeout=30):
        for ident in present:
            if f"obo_id={ident}" in url:
                return 200, {"page": {"totalElements": 1}}
        return 404, None

    return _http_get


def test_wellformed_present_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "MONDO:0005148"
    assert res.suggestion is None
    assert res.how == "remote"
    assert res.version is not None


def test_wellformed_absent_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biogate.check_id("MONDO:9999999", source_db="mondo", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_malformed_with_existing_correction_suggests(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biogate.check_id("mondo:5148", source_db="mondo", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "MONDO:0005148"


def test_source_without_remote_block_raises(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present(set()))
    with pytest.raises(NoResolverError):
        biogate.check_id("ENSG00000139618", source_db="ensembl", how="remote")


def test_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 500, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")


def test_disk_cache_short_circuits_network(monkeypatch):
    path = remote._remote_cache_path("mondo", "MONDO:0005148")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"status": 200, "body": {"page": {"totalElements": 1}}}),
        encoding="utf-8",
    )

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called when cache hits")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True


def test_corrupt_cache_is_ignored_and_refetched(monkeypatch):
    path = remote._remote_cache_path("mondo", "MONDO:0005148")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not valid json", encoding="utf-8")

    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True


def test_parse_body_tolerates_empty_and_non_json():
    assert remote._parse_body("") is None
    assert remote._parse_body("   ") is None
    assert remote._parse_body("<html>Bad Gateway</html>") is None
    assert remote._parse_body('{"page": {"totalElements": 2}}') == {
        "page": {"totalElements": 2}
    }


def test_ols_count_handles_missing_null_and_malformed():
    assert remote._ols_count(None) == 0
    assert remote._ols_count({"page": None}) == 0
    assert remote._ols_count({"page": {}}) == 0
    assert remote._ols_count({"page": {"totalElements": None}}) == 0
    assert remote._ols_count({"page": {"totalElements": 3}}) == 3
