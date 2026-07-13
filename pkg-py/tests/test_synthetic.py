"""The synthetic column generator: correctness, determinism, and fixture parity."""

import json
from importlib.resources import files

import pytest

import biobouncer as bb
from biobouncer.core import check_id

_COLUMNS = files("biobouncer") / "_data" / "fixtures" / "columns"
_SOURCES = sorted(bb.sources())
_CACHE_SOURCES = sorted(
    row["key"] for row in bb.source_info() if "cache" in row["modes"]
)

# The only sources with no pattern-mode repairable form (no curie or normalize).
_NO_REPAIRABLE = {"ec", "hgnc", "hgvs"}


@pytest.fixture(autouse=True)
def _bundled_cache(tmp_path, monkeypatch):
    # Force cache mode to the bundled sample snapshots, as the fixtures were built.
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _category(result) -> str:
    if result.valid is True:
        return "valid"
    if result.valid is None:
        return "missing"
    if result.suggestion is not None:
        return "repairable"
    return "invalid"


def _fixture_rows(source_db):
    path = _COLUMNS / f"{source_db}.cases.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.parametrize("source_db", _SOURCES)
def test_synthesize_is_deterministic(source_db):
    assert bb.synthesize(source_db) == bb.synthesize(source_db)


@pytest.mark.parametrize("source_db", _SOURCES)
def test_labels_are_self_consistent(source_db):
    # Every row's category and verdict fields must match a fresh pattern check.
    for row in bb.synthesize(source_db):
        result = check_id([row["input"]], source_db, how="pattern")[0]
        assert row["category"] == _category(result)
        assert row["valid"] == result.valid
        assert row["normalized"] == result.normalized
        assert row["suggestion"] == result.suggestion


@pytest.mark.parametrize("source_db", _SOURCES)
def test_covers_expected_categories(source_db):
    categories = {row["category"] for row in bb.synthesize(source_db)}
    assert {"valid", "invalid", "missing"} <= categories
    if source_db in _NO_REPAIRABLE:
        assert "repairable" not in categories
    else:
        assert "repairable" in categories


@pytest.mark.parametrize("source_db", _SOURCES)
def test_reproduces_committed_fixture(source_db):
    # The generator is the source of truth for the committed fixtures; this is the
    # cross-language parity + freshness gate (R must reproduce the same files).
    produced = [
        {
            "input": row["input"],
            "source_db": source_db,
            "how": "pattern",
            "category": row["category"],
            "expect": {
                "valid": row["valid"],
                "normalized": row["normalized"],
                "suggestion": row["suggestion"],
            },
        }
        for row in bb.synthesize(source_db)
    ]
    assert produced == _fixture_rows(source_db)


def test_unknown_source_raises():
    with pytest.raises(bb.UnknownSourceError):
        bb.synthesize("not_a_source")


def _cache_fixture_rows(source_db):
    path = _COLUMNS / f"{source_db}.cache.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_synthesize_is_deterministic(source_db):
    assert bb.synthesize(source_db, how="cache") == bb.synthesize(
        source_db, how="cache"
    )


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_covers_all_categories(source_db):
    categories = {row["category"] for row in bb.synthesize(source_db, how="cache")}
    assert categories == {"valid", "repairable", "invalid", "missing"}


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_labels_are_self_consistent(source_db):
    for row in bb.synthesize(source_db, how="cache", version="sample"):
        result = check_id([row["input"]], source_db, how="cache", version="sample")[0]
        assert row["category"] == _category(result)
        assert row["valid"] == result.valid
        assert row["suggestion"] == result.suggestion


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_reproduces_committed_fixture(source_db):
    produced = [
        {
            "input": row["input"],
            "source_db": source_db,
            "how": "cache",
            "version": "sample",
            "category": row["category"],
            "expect": {
                "valid": row["valid"],
                "normalized": row["normalized"],
                "suggestion": row["suggestion"],
            },
        }
        for row in bb.synthesize(source_db, how="cache", version="sample")
    ]
    assert produced == _cache_fixture_rows(source_db)
