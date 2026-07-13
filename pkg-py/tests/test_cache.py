"""Cache mode behavior against the bundled sample snapshot."""

import pytest

import biobouncer
from biobouncer import MissingSnapshotError


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def test_cache_checks_existence():
    res = biobouncer.check_id(
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
    res = biobouncer.check_id(
        "mondo:9999999", source_db="mondo", how="cache", version="sample"
    )[0]
    assert res.valid is False
    assert res.suggestion is None


def test_cache_defaults_to_latest_installed_snapshot():
    # With no version, cache mode uses the latest installed snapshot instead of
    # forcing a magic version="sample". The bundled sample is the only one here.
    res = biobouncer.check_id("MONDO:0005148", source_db="mondo", how="cache")[0]
    assert res.valid is True
    assert res.version == "sample"


def test_cache_default_prefers_pinned_default_version():
    # hgnc pins default_version; the default resolves to it, not the sample.
    res = biobouncer.check_id("TP53", source_db="hgnc", how="cache")[0]
    assert res.valid is True
    assert res.version == "2026-07-07"


def test_cache_defaults_for_newly_snapshotted_obo_source():
    # doid now ships a bundled sample snapshot, so a defaulted cache check
    # resolves to it instead of erroring.
    res = biobouncer.check_id("DOID:9352", source_db="doid", how="cache")[0]
    assert res.valid is True
    assert res.version == "sample"


def test_missing_snapshot_errors():
    with pytest.raises(MissingSnapshotError):
        biobouncer.check_id(
            "MONDO:0005148", source_db="mondo", how="cache", version="2099-01"
        )


@pytest.mark.parametrize(
    "version", ["../../etc/passwd", "..\\..\\secret", "a/b", "sub/../x", ""]
)
def test_cache_rejects_traversal_version(version):
    # A version that could escape the snapshot directory is refused, not read.
    from biobouncer._cache import InvalidVersionError

    with pytest.raises(InvalidVersionError):
        biobouncer.check_id(
            "MONDO:0005148", source_db="mondo", how="cache", version=version
        )


def test_pull_rejects_traversal_version():
    from biobouncer._cache import InvalidVersionError

    with pytest.raises(InvalidVersionError):
        biobouncer.pull("mondo", version="../../evil")


def test_cache_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    assert biobouncer.cache_dir() == tmp_path


def test_snapshots_lists_bundled_sample():
    snaps = biobouncer.snapshots()
    mondo = [s for s in snaps if s["source"] == "mondo" and s["version"] == "sample"]
    assert len(mondo) == 1
    assert mondo[0]["location"] == "bundled"
    assert mondo[0]["n_ids"] > 0


def test_snapshots_include_the_new_obo_samples():
    snaps = biobouncer.snapshots()
    bundled = {
        s["source"]
        for s in snaps
        if s["version"] == "sample" and s["location"] == "bundled"
    }
    assert {"bto", "cl", "doid", "hp", "mp", "pato", "so", "uberon"} <= bundled
