"""HGVS remote mode: existence via the Mutalyzer normalizer, network stubbed."""

import pytest

import biobouncer
import biobouncer._remote as remote
from biobouncer import RemoteError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _stub_status(status, body=None):
    def _http_get(url, timeout=30):
        return status, body

    return _http_get


def test_safe_ident_replaces_unsafe_characters():
    assert remote._safe_ident("NM_004006.2:c.4375C>T") == "NM_004006.2_c.4375C_T"
    assert remote._safe_ident("A/B C") == "A_B_C"
    # a plain accession keeps its dot and underscore
    assert remote._safe_ident("NM_004006.2") == "NM_004006.2"


def test_cache_path_has_no_unsafe_characters():
    path = remote._remote_cache_path("mutalyzer", "normalize", "NM_004006.2:c.4375C>T")
    assert ">" not in path.name and ":" not in path.name
    assert path.name == "NM_004006.2_c.4375C_T.json"


def test_valid_variant_is_valid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_status(200))
    res = biobouncer.check_id("NM_004006.2:c.4375C>T", source_db="hgvs", how="remote")[
        0
    ]
    assert res.valid is True
    assert res.normalized == "NM_004006.2:c.4375C>T"
    assert res.suggestion is None
    assert res.how == "remote"


def test_reference_inconsistent_variant_is_invalid(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_status(422))
    res = biobouncer.check_id("NM_004006.2:c.4375A>T", source_db="hgvs", how="remote")[
        0
    ]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_malformed_variant_skips_the_network(monkeypatch):
    def _forbidden(url, timeout=30):
        raise AssertionError("a malformed variant must not reach the network")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    # insertion without a flanking range fails the offline grammar first
    res = biobouncer.check_id("NM_004006.2:c.76insG", source_db="hgvs", how="remote")[0]
    assert res.valid is False
    assert res.suggestion is None


def test_unexpected_status_raises_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_status(500))
    with pytest.raises(RemoteError):
        biobouncer.check_id("NM_004006.2:c.4375C>T", source_db="hgvs", how="remote")
    path = remote._remote_cache_path("mutalyzer", "normalize", "NM_004006.2:c.4375C>T")
    assert not path.is_file()


def test_cache_round_trip(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_status(200))
    assert biobouncer.check_id("NM_004006.2:c.4375C>T", source_db="hgvs", how="remote")[
        0
    ].valid

    def _forbidden(url, timeout=30):
        raise AssertionError("network should not be called on a cache hit")

    monkeypatch.setattr(remote, "_http_get", _forbidden)
    assert biobouncer.check_id("NM_004006.2:c.4375C>T", source_db="hgvs", how="remote")[
        0
    ].valid
