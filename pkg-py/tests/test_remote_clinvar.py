"""ClinVar remote mode: live existence checks via NCBI E-utilities esearch."""

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


def _hits(n=1):
    return {"esearchresult": {"count": str(n)}}


def test_url_builds_the_esearch_endpoint():
    from biobouncer._registry import get_source

    url = remote._clinvar_url(get_source("clinvar"), "VCV000012345")
    assert url == (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        "?db=clinvar&term=VCV000012345&retmode=json"
    )


def test_existing_accession_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(1)))
    res = biobouncer.check_id("VCV000012345", source_db="clinvar", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "VCV000012345"
    assert res.suggestion is None


def test_absent_accession_is_invalid(monkeypatch):
    # esearch answers 200 with a zero count for an accession with no hits.
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(0)))
    res = biobouncer.check_id("VCV999999999", source_db="clinvar", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _hits(1)))
    res = biobouncer.check_id("vcv000012345", source_db="clinvar", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "VCV000012345"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id("VCV12345", source_db="clinvar", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("VCV000012345", source_db="clinvar", how="remote")
    path = remote._remote_cache_path("clinvar", "esearch", "VCV000012345")
    assert not path.is_file()
