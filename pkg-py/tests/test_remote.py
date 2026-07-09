"""Remote mode behavior, fully offline by monkeypatching the network seam."""

import json

import pytest

import biogate
import biogate._remote as remote
from biogate import NoResolverError, RemoteError
from biogate._registry import Source


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


def _source(remote_block):
    """Build a minimal Source with the given remote block for resolver tests."""
    return Source(
        key="fake",
        name="Fake",
        description="",
        pattern="X[0-9]+",
        species_aware=False,
        version_aware=False,
        curie=None,
        normalize=None,
        cache=None,
        remote=remote_block,
    )


def test_source_without_remote_block_raises():
    with pytest.raises(NoResolverError):
        remote._get_resolver(_source(None))


def test_source_with_unknown_resolver_raises():
    with pytest.raises(NoResolverError):
        remote._get_resolver(_source({"resolver": "nope"}))


def test_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 500, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")
    # An indeterminate status must not be cached.
    assert not remote._remote_cache_path("ols", "mondo", "MONDO:0005148").is_file()


def test_disk_cache_short_circuits_network(monkeypatch):
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
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
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
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


def _stub_ensembl(present):
    """Return a _http_get stub where ids in ``present`` answer 200, others 400."""

    def _http_get(url, timeout=30):
        for ident in present:
            if f"/lookup/id/{ident}?" in url:
                return 200, None
        return 400, None

    return _http_get


def _stub_uniprot(active):
    """Return a _http_get stub where ids in ``active`` are active UniProtKB."""

    def _http_get(url, timeout=30):
        for ident in active:
            if f"/uniprotkb/{ident}.json" in url:
                return 200, {"entryType": "UniProtKB reviewed (Swiss-Prot)"}
        return 200, {"entryType": "Inactive"}

    return _http_get


def test_ensembl_present_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl({"ENSG00000139618"}))
    res = biogate.check_id("ENSG00000139618", source_db="ensembl", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "ENSG00000139618"
    assert res.suggestion is None


def test_ensembl_absent_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl(set()))
    res = biogate.check_id("ENSG00000000000", source_db="ensembl", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_ensembl_lowercase_suggests_uppercase(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl({"ENSG00000139618"}))
    res = biogate.check_id("ensg00000139618", source_db="ensembl", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "ENSG00000139618"


def test_uniprot_active_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    res = biogate.check_id("P01308", source_db="uniprot", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "P01308"
    assert res.suggestion is None


def test_uniprot_inactive_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot(set()))
    res = biogate.check_id("O99999", source_db="uniprot", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_uniprot_lowercase_suggests_active_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    res = biogate.check_id("p01308", source_db="uniprot", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "P01308"


def test_ensembl_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 500, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biogate.check_id("ENSG00000139618", source_db="ensembl", how="remote")
    assert not remote._remote_cache_path("ensembl", "id", "ENSG00000139618").is_file()


def test_uniprot_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 503, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biogate.check_id("P01308", source_db="uniprot", how="remote")
    assert not remote._remote_cache_path("uniprot", "uniprotkb", "P01308").is_file()


def test_ensembl_cache_round_trip(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl({"ENSG00000139618"}))
    assert biogate.check_id("ENSG00000139618", source_db="ensembl", how="remote")[
        0
    ].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert biogate.check_id("ENSG00000139618", source_db="ensembl", how="remote")[
        0
    ].valid


def test_uniprot_cache_round_trip(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    assert biogate.check_id("P01308", source_db="uniprot", how="remote")[0].valid
    # A retired accession must round-trip through the cache as invalid.
    assert not biogate.check_id("O99999", source_db="uniprot", how="remote")[0].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert biogate.check_id("P01308", source_db="uniprot", how="remote")[0].valid
    assert not biogate.check_id("O99999", source_db="uniprot", how="remote")[0].valid


def test_uniprot_active_predicate():
    assert remote._uniprot_active({"entryType": "UniProtKB reviewed (Swiss-Prot)"})
    assert remote._uniprot_active({"entryType": "UniProtKB unreviewed (TrEMBL)"})
    assert not remote._uniprot_active({"entryType": "Inactive"})
    assert not remote._uniprot_active({})
    assert not remote._uniprot_active(None)
