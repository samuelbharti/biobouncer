"""Existence mode: snapshot when one is available for the version, else remote.

Each test installs a network stub that errors when it should not be reached, so
the chosen path (snapshot vs live) is unambiguous.
"""

import biobouncer
import biobouncer._remote as remote


def _forbidden(url, timeout=30):
    raise AssertionError("existence must use the snapshot, not the network")


def _stub_mondo_present(url, timeout=30):
    if "obo_id=MONDO:0005148" in url:
        return 200, {"page": {"totalElements": 1}}
    return 404, None


def test_existence_uses_snapshot_when_version_available(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id(
        ["MONDO:0005148", "MONDO:9999999", "mondo:5148"],
        source_db="mondo",
        how="existence",
        version="sample",
    )
    assert [r.valid for r in res] == [True, False, False]
    assert [r.normalized for r in res] == ["MONDO:0005148", None, None]
    assert [r.suggestion for r in res] == [None, None, "MONDO:0005148"]
    assert all(r.how == "existence" for r in res)
    assert all(r.version == "sample" for r in res)


def test_existence_falls_back_to_remote_without_version(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_get", _stub_mondo_present)
    res = biobouncer.check_id(
        ["MONDO:0005148", "MONDO:9999999"], source_db="mondo", how="existence"
    )
    assert [r.valid for r in res] == [True, False]
    assert all(r.how == "existence" for r in res)
    assert all(r.version and r.version != "sample" for r in res)


def test_existence_falls_back_when_snapshot_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_get", _stub_mondo_present)
    res = biobouncer.check_id(
        "MONDO:0005148", source_db="mondo", how="existence", version="2099-01-01"
    )[0]
    assert res.valid is True
    assert res.version != "2099-01-01"


def test_existence_uses_remote_for_source_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))

    def _uniprot(url, timeout=30):
        if "/uniprotkb/P01308.json" in url:
            return 200, {"entryType": "UniProtKB reviewed (Swiss-Prot)"}
        return 404, None

    monkeypatch.setattr(remote, "_http_get", _uniprot)
    res = biobouncer.check_id("P01308", source_db="uniprot", how="existence")[0]
    assert res.valid is True


def test_existence_degrades_to_pattern_for_pattern_only_source(monkeypatch):
    # cosmic is pattern-only: no snapshot and no resolver. Existence degrades to
    # a shape check instead of raising NoResolverError. No network is touched.
    monkeypatch.setattr(remote, "_http_get", _forbidden)
    res = biobouncer.check_id(
        ["COSM476", "nonsense"], source_db="cosmic", how="existence"
    )
    assert [r.valid for r in res] == [True, False]
    assert all(r.how == "existence" for r in res)
    assert res[0].version is None
