"""Species gating in remote mode, fully offline by stubbing the network seam."""

import pytest

import biobouncer
import biobouncer._remote as remote


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _stub(status, body):
    """Return a _http_get stub that answers every url with ``(status, body)``."""

    def _http_get(url, timeout=30):
        return status, body

    return _http_get


_HUMAN_BODY = {
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "organism": {"taxonId": 9606},
}


def test_ensembl_species_match_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, None))
    res = biobouncer.check_id(
        "ENSMUSG00000059552", source_db="ensembl", how="remote", species="mus_musculus"
    )[0]
    assert res.valid is True
    assert res.normalized == "ENSMUSG00000059552"


def test_ensembl_species_mismatch_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, None))
    res = biobouncer.check_id(
        "ENSMUSG00000059552", source_db="ensembl", how="remote", species="homo_sapiens"
    )[0]
    assert res.valid is False
    assert res.normalized is None


def test_uniprot_species_match_by_name_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _HUMAN_BODY))
    res = biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="homo_sapiens"
    )[0]
    assert res.valid is True
    assert res.normalized == "P01308"


def test_uniprot_species_match_by_taxon_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _HUMAN_BODY))
    res = biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species=9606
    )[0]
    assert res.valid is True


def test_uniprot_species_mismatch_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _HUMAN_BODY))
    res = biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="mus_musculus"
    )[0]
    assert res.valid is False
    assert res.normalized is None


def test_unknown_species_is_lenient(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _HUMAN_BODY))
    res = biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="unknown_species"
    )[0]
    assert res.valid is True


def test_uniprot_species_round_trips_through_cache(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub(200, _HUMAN_BODY))
    assert biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="homo_sapiens"
    )[0].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    # The cached organism still supports the species check both ways.
    assert biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="homo_sapiens"
    )[0].valid
    assert not biobouncer.check_id(
        "P01308", source_db="uniprot", how="remote", species="mus_musculus"
    )[0].valid
