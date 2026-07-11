"""miRBase remote mode: existence via RNAcentral through EBI Search."""

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


def _hits(n=1):
    return {"hitCount": n}


def test_url_builds_the_ebi_search_endpoint():
    from biogate._registry import get_source

    url = remote._mirbase_url(get_source("mirbase"), "MIMAT0000001")
    assert url == (
        "https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral"
        "?query=MIMAT0000001&format=json"
    )


def test_existing_accession_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(1)))
    res = biogate.check_id("MIMAT0000001", source_db="mirbase", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "MIMAT0000001"
    assert res.suggestion is None


def test_absent_accession_is_invalid(monkeypatch):
    # EBI Search answers 200 with a zero hit count for an unknown accession.
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(0)))
    res = biogate.check_id("MIMAT9999999", source_db="mirbase", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(1)))
    res = biogate.check_id("mimat0000001", source_db="mirbase", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "MIMAT0000001"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biogate.check_id("MIMAT001", source_db="mirbase", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biogate.check_id("MIMAT0000001", source_db="mirbase", how="remote")
    path = remote._remote_cache_path("mirbase", "rnacentral", "MIMAT0000001")
    assert not path.is_file()
