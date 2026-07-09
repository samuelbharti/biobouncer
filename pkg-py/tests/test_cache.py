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


def test_cache_requires_version():
    with pytest.raises(MissingVersionError):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="cache")


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
