"""Cache mode behavior against the bundled sample snapshot."""

import pytest

import biogate
from biogate import MissingSnapshotError, MissingVersionError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def test_cache_checks_existence():
    res = biogate.check_id(
        ["MONDO:0005148", "MONDO:9999999", "mondo:5148"],
        source_db="mondo",
        how="cache",
        version="sample",
    )
    assert [r.valid for r in res] == [True, False, False]
    assert res[0].normalized == "MONDO:0005148"
    assert res[2].suggestion == "MONDO:0005148"
    assert all(r.how == "cache" for r in res)
    assert all(r.version == "sample" for r in res)


def test_absent_suggestion_is_not_offered():
    res = biogate.check_id(
        "mondo:9999999", source_db="mondo", how="cache", version="sample"
    )[0]
    assert res.valid is False
    assert res.suggestion is None


def test_cache_defaults_to_latest_installed_snapshot():
    # With no version, cache mode uses the latest installed snapshot instead of
    # forcing a magic version="sample". The bundled sample is the only one here.
    res = biogate.check_id("MONDO:0005148", source_db="mondo", how="cache")[0]
    assert res.valid is True
    assert res.version == "sample"


def test_cache_default_prefers_pinned_default_version():
    # hgnc pins default_version; the default resolves to it, not the sample.
    res = biogate.check_id("TP53", source_db="hgnc", how="cache")[0]
    assert res.valid is True
    assert res.version == "2026-07-07"


def test_cache_no_snapshot_installed_errors():
    # doid declares cache mode but ships no bundled snapshot, so a defaulted
    # cache check with nothing installed is an actionable error, not a crash.
    with pytest.raises(MissingVersionError):
        biogate.check_id("DOID:9352", source_db="doid", how="cache")


def test_missing_snapshot_errors():
    with pytest.raises(MissingSnapshotError):
        biogate.check_id(
            "MONDO:0005148", source_db="mondo", how="cache", version="2099-01"
        )


def test_cache_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))
    assert biogate.cache_dir() == tmp_path


def test_snapshots_lists_bundled_sample():
    snaps = biogate.snapshots()
    mondo = [s for s in snaps if s["source"] == "mondo" and s["version"] == "sample"]
    assert len(mondo) == 1
    assert mondo[0]["location"] == "bundled"
    assert mondo[0]["n_ids"] > 0
