"""RefSeq remote mode: live existence checks via NCBI E-utilities esummary."""

import pytest

import biobouncer
import biobouncer._remote as remote
from biobouncer import RemoteError

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _stub(status, body=None):
    def _http_get(url, timeout=30):
        return status, body

    return _http_get


def _found(uid="1808862652"):
    return {"result": {"uids": [uid]}}


def test_url_routes_by_molecule_prefix():
    from biobouncer._registry import get_source

    src = get_source("refseq")
    assert remote._refseq_url(src, "NM_000546.6") == (
        f"{_BASE}?db=nuccore&id=NM_000546.6&retmode=json"
    )
    # A protein prefix routes to the protein database.
    assert remote._refseq_url(src, "NP_003997.1") == (
        f"{_BASE}?db=protein&id=NP_003997.1&retmode=json"
    )


def test_existing_accession_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _found()))
    res = biobouncer.check_id("NM_000546.6", source_db="refseq", how="remote")[0]
    assert res.valid is True
    assert res.normalized == "NM_000546.6"
    assert res.suggestion is None


def test_absent_accession_is_invalid(monkeypatch):
    # esummary answers 200 with an empty uid list for an unknown accession.
    monkeypatch.setattr(remote, "_http_get", _stub(200, {"result": {"uids": []}}))
    res = biobouncer.check_id("NM_999999999", source_db="refseq", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_lowercase_suggests_the_uppercase_form(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _found()))
    res = biobouncer.check_id("nm_000546.6", source_db="refseq", how="remote")[0]
    assert res.valid is False
    assert res.suggestion == "NM_000546.6"


def test_malformed_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed id must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id("QQ_000546", source_db="refseq", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("NM_000546.6", source_db="refseq", how="remote")
    path = remote._remote_cache_path("refseq", "esummary", "NM_000546.6")
    assert not path.is_file()
