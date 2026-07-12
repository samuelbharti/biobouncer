"""Remote mode behavior, fully offline by monkeypatching the network seam."""

import json

import pytest

import biobouncer
import biobouncer._remote as remote
from biobouncer import NoResolverError, RemoteError
from biobouncer._registry import Source


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


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
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "MONDO:0005148"
    assert res.suggestion is None
    assert res.how == "remote"
    assert res.version is not None


def test_wellformed_absent_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biobouncer.check_id("MONDO:9999999", source_db="mondo", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_malformed_with_existing_correction_suggests(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biobouncer.check_id("mondo:5148", source_db="mondo", how="remote")[0]
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
        biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")
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
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True


def test_corrupt_cache_is_ignored_and_refetched(monkeypatch):
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not valid json", encoding="utf-8")

    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True


def _seed_cache(path, *, status, body, fetched_at, url="http://x"):
    """Write a remote cache record with a chosen fetch time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"status": status, "body": body, "url": url, "fetched_at": fetched_at}
        ),
        encoding="utf-8",
    )


def _forbid_network(url, timeout=30):
    raise AssertionError("network should not be called when the cache is used")


def test_fetch_records_its_time_and_uses_it_as_version(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    record = json.loads(
        remote._remote_cache_path("ols", "mondo", "MONDO:0005148").read_text("utf-8")
    )
    assert record["fetched_at"]  # the fetch time is written into the cache record
    assert res.version == record["fetched_at"]  # and reported as the result version


def test_cached_verdict_reports_its_original_fetch_time(monkeypatch):
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
    _seed_cache(
        path,
        status=200,
        body={"page": {"totalElements": 1}},
        fetched_at="2000-01-01T00:00:00Z",
    )
    monkeypatch.setattr(remote, "_http_get", _forbid_network)
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True
    # The verdict came from the cache, so its version is the original fetch time,
    # not the time of this run.
    assert res.version == "2000-01-01T00:00:00Z"


def test_refresh_bypasses_the_cache(monkeypatch):
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
    _seed_cache(path, status=404, body=None, fetched_at="2000-01-01T00:00:00Z")
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    stale = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert stale.valid is False  # served from the cached "absent" record
    fresh = biobouncer.check_id(
        "MONDO:0005148", source_db="mondo", how="remote", refresh=True
    )[0]
    assert fresh.valid is True  # refetched, ignoring the cache
    assert fresh.version != "2000-01-01T00:00:00Z"


def test_ttl_expiry_refetches(monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_REMOTE_TTL", "1")
    path = remote._remote_cache_path("ols", "mondo", "MONDO:0005148")
    _seed_cache(path, status=404, body=None, fetched_at="2000-01-01T00:00:00Z")
    monkeypatch.setattr(remote, "_http_get", _stub_present({"MONDO:0005148"}))
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True  # the cached record aged past the TTL, so it refetched


def test_remote_ttl_reads_the_environment(monkeypatch):
    monkeypatch.delenv("BIOBOUNCER_REMOTE_TTL", raising=False)
    assert remote._remote_ttl() is None
    for off in ("0", "-5", "not-a-number"):
        monkeypatch.setenv("BIOBOUNCER_REMOTE_TTL", off)
        assert remote._remote_ttl() is None
    monkeypatch.setenv("BIOBOUNCER_REMOTE_TTL", "3600")
    assert remote._remote_ttl() == 3600.0


def test_is_stale_rules():
    assert remote._is_stale("2000-01-01T00:00:00Z", None) is False  # no TTL, never
    assert remote._is_stale(None, 100) is True  # no timestamp to trust
    assert remote._is_stale("garbage", 100) is True  # unparseable
    assert remote._is_stale("2000-01-01T00:00:00Z", 100) is True  # long expired
    assert remote._is_stale(remote._utc_stamp(), 3600) is False  # fresh


def test_transient_status_is_retried_then_succeeds(monkeypatch):
    calls = []

    def _once(url, timeout=30):
        calls.append(url)
        if len(calls) < 3:
            return 503, None  # transient server error
        return 200, {"page": {"totalElements": 1}}

    monkeypatch.setattr(remote, "_http_get_once", _once)
    monkeypatch.setattr(remote.time, "sleep", lambda seconds: None)
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")[0]
    assert res.valid is True
    assert len(calls) == 3  # two retries, then the success


def test_persistent_network_error_is_retried_then_raised(monkeypatch):
    calls = []

    def _once(url, timeout=30):
        calls.append(url)
        raise RemoteError("connection reset")

    monkeypatch.setattr(remote, "_http_get_once", _once)
    monkeypatch.setattr(remote.time, "sleep", lambda seconds: None)
    with pytest.raises(RemoteError):
        biobouncer.check_id("MONDO:0005148", source_db="mondo", how="remote")
    assert len(calls) == remote._MAX_ATTEMPTS  # exhausted every attempt


def test_non_transient_status_is_not_retried(monkeypatch):
    calls = []

    def _once(url, timeout=30):
        calls.append(url)
        return 404, None  # a definite "absent", not transient

    monkeypatch.setattr(remote, "_http_get_once", _once)
    monkeypatch.setattr(remote.time, "sleep", lambda seconds: None)
    res = biobouncer.check_id("MONDO:9999999", source_db="mondo", how="remote")[0]
    assert res.valid is False
    assert len(calls) == 1  # answered on the first try


def test_ncbi_suffix_added_only_when_a_key_is_configured(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    assert remote._ncbi_suffix() == ""  # no key, URL unchanged
    assert "api_key" not in remote._refseq_url(None, "NM_000546")
    assert "api_key" not in remote._clinvar_url(None, "VCV000012345")

    monkeypatch.setenv("NCBI_API_KEY", "secret")
    suffix = remote._ncbi_suffix()
    assert suffix.startswith("&")
    assert "api_key=secret" in suffix
    assert "tool=biobouncer" in suffix
    assert "api_key=secret" in remote._refseq_url(None, "NM_000546")

    monkeypatch.setenv("NCBI_EMAIL", "a@b.co")
    assert "email=a%40b.co" in remote._ncbi_suffix()


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
    res = biobouncer.check_id("ENSG00000139618", source_db="ensembl", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "ENSG00000139618"
    assert res.suggestion is None


def test_ensembl_absent_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl(set()))
    res = biobouncer.check_id("ENSG00000000000", source_db="ensembl", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_ensembl_lowercase_suggests_uppercase(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl({"ENSG00000139618"}))
    res = biobouncer.check_id("ensg00000139618", source_db="ensembl", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "ENSG00000139618"


def test_uniprot_active_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    res = biobouncer.check_id("P01308", source_db="uniprot", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "P01308"
    assert res.suggestion is None


def test_uniprot_inactive_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot(set()))
    res = biobouncer.check_id("O99999", source_db="uniprot", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_uniprot_lowercase_suggests_active_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    res = biobouncer.check_id("p01308", source_db="uniprot", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "P01308"


def test_ensembl_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 500, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biobouncer.check_id("ENSG00000139618", source_db="ensembl", how="remote")
    assert not remote._remote_cache_path("ensembl", "id", "ENSG00000139618").is_file()


def test_uniprot_unexpected_status_raises_remote_error(monkeypatch):
    def _http_get(url, timeout=30):
        return 503, None

    monkeypatch.setattr(remote, "_http_get", _http_get)
    with pytest.raises(RemoteError):
        biobouncer.check_id("P01308", source_db="uniprot", how="remote")
    assert not remote._remote_cache_path("uniprot", "uniprotkb", "P01308").is_file()


def test_ensembl_cache_round_trip(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_ensembl({"ENSG00000139618"}))
    assert biobouncer.check_id("ENSG00000139618", source_db="ensembl", how="remote")[
        0
    ].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert biobouncer.check_id("ENSG00000139618", source_db="ensembl", how="remote")[
        0
    ].valid


def test_uniprot_cache_round_trip(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_uniprot({"P01308"}))
    assert biobouncer.check_id("P01308", source_db="uniprot", how="remote")[0].valid
    # A retired accession must round-trip through the cache as invalid.
    assert not biobouncer.check_id("O99999", source_db="uniprot", how="remote")[0].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert biobouncer.check_id("P01308", source_db="uniprot", how="remote")[0].valid
    assert not biobouncer.check_id("O99999", source_db="uniprot", how="remote")[0].valid


def test_uniprot_active_predicate():
    assert remote._uniprot_active({"entryType": "UniProtKB reviewed (Swiss-Prot)"})
    assert remote._uniprot_active({"entryType": "UniProtKB unreviewed (TrEMBL)"})
    assert not remote._uniprot_active({"entryType": "Inactive"})
    assert not remote._uniprot_active({})
    assert not remote._uniprot_active(None)
