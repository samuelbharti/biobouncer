"""Version-retirement support: remote obsolete terms and cache retired maps."""

import pytest

import biogate
import biogate._remote as remote
from biogate._cache import _snapshot_retired
from biogate._remote import _normalize_obo


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def test_normalize_obo_short_form():
    assert _normalize_obo("GO_0006915") == "GO:0006915"


def test_normalize_obo_full_iri():
    iri = "http://purl.obolibrary.org/obo/MONDO_0005016"
    assert _normalize_obo(iri) == "MONDO:0005016"


def test_normalize_obo_empty_and_none():
    assert _normalize_obo(None) is None
    assert _normalize_obo("") is None


def _stub_obsolete(ident, term_replaced_by):
    """Return a _http_get stub serving one obsolete OLS term for ``ident``."""

    def _http_get(url, timeout=30):
        if f"obo_id={ident}" in url:
            return 200, {
                "page": {"totalElements": 1},
                "_embedded": {
                    "terms": [
                        {"is_obsolete": True, "term_replaced_by": term_replaced_by}
                    ]
                },
            }
        return 404, None

    return _http_get


def test_remote_obsolete_suggests_successor(monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _stub_obsolete("GO:0006917", "GO_0006915"))
    res = biogate.check_id("GO:0006917", source_db="go", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "GO:0006915"


def test_remote_obsolete_cross_ontology_successor(monkeypatch):
    iri = "http://purl.obolibrary.org/obo/MONDO_0005016"
    monkeypatch.setattr(remote, "_http_get", _stub_obsolete("EFO:0000401", iri))
    res = biogate.check_id("EFO:0000401", source_db="efo", how="remote")[0]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "MONDO:0005016"


def test_cache_retired_suggests_successor():
    res = biogate.check_id("GO:0006917", source_db="go", how="cache", version="sample")[
        0
    ]
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == "GO:0006915"


def test_cache_not_retired_has_no_suggestion():
    res = biogate.check_id("GO:0000001", source_db="go", how="cache", version="sample")[
        0
    ]
    assert res.valid is False
    assert res.suggestion is None


def test_snapshot_retired_map_for_go_sample():
    assert _snapshot_retired("go", "sample") == {"GO:0006917": "GO:0006915"}
