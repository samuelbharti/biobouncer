"""Per-source synthetic columns exercise report/repair and the adapters uniformly.

The committed fixtures under _data/fixtures/columns give every source a mixed
column (valid / repairable / invalid / missing). These tests run the same column
through report(), repair(), is_valid_id, and the framework adapters, so all 46
sources get column-level coverage, not just mondo and hgnc.
"""

import json
from importlib.resources import files

import pytest

import biobouncer as bb

_COLUMNS = files("biobouncer") / "_data" / "fixtures" / "columns"
_SOURCES = sorted(bb.sources())
_CACHE_SOURCES = sorted(
    row["key"] for row in bb.source_info() if "cache" in row["modes"]
)


@pytest.fixture(autouse=True)
def _bundled_cache(tmp_path, monkeypatch):
    # Force cache mode to the bundled sample snapshots, as the fixtures were built.
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def _load(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rows(source_db):
    return _load(_COLUMNS / f"{source_db}.cases.jsonl")


def _cache_rows(source_db):
    return _load(_COLUMNS / f"{source_db}.cache.jsonl")


def _column(rows):
    return [row["input"] for row in rows]


@pytest.mark.parametrize("source_db", _SOURCES)
def test_report_summary_matches_categories(source_db):
    rows = _rows(source_db)
    categories = [row["category"] for row in rows]
    summary = bb.report(_column(rows), source_db, how="pattern").summary
    assert summary["total"] == len(rows)
    assert summary["valid"] == categories.count("valid")
    assert summary["repairable"] == categories.count("repairable")
    # invalid counts every failed value: the hard invalids plus the repairables.
    assert summary["invalid"] == categories.count("invalid") + categories.count(
        "repairable"
    )
    assert summary["missing"] == categories.count("missing")
    assert summary["indeterminate"] == 0


@pytest.mark.parametrize("source_db", _SOURCES)
def test_repair_substitutes_only_the_repairable_cells(source_db):
    rows = _rows(source_db)
    expected = [
        row["expect"]["suggestion"] if row["category"] == "repairable" else row["input"]
        for row in rows
    ]
    assert bb.report(_column(rows), source_db, how="pattern").repair() == expected


@pytest.mark.parametrize("source_db", _SOURCES)
def test_is_valid_id_per_row(source_db):
    rows = _rows(source_db)
    verdicts = bb.is_valid_id(_column(rows), source_db, how="pattern")
    for row, verdict in zip(rows, verdicts):
        if row["category"] == "valid":
            assert verdict is True
        elif row["category"] == "missing":
            assert verdict is None
        else:
            assert verdict is False


@pytest.mark.parametrize("source_db", _SOURCES)
def test_narwhals_mask_over_the_column(source_db):
    pytest.importorskip("narwhals")
    pd = pytest.importorskip("pandas")
    from biobouncer.narwhals import valid_id_mask

    rows = _rows(source_db)
    mask = list(
        valid_id_mask(pd.Series(_column(rows), name="id"), source_db, how="pattern")
    )
    for row, passes in zip(rows, mask):
        # Only an explicit failure masks False; a missing cell passes.
        assert passes == (row["category"] not in ("repairable", "invalid"))


@pytest.mark.parametrize("source_db", _SOURCES)
def test_pandera_flags_the_messy_column(source_db):
    pytest.importorskip("pandera")
    pd = pytest.importorskip("pandas")
    import pandera.pandas as pa

    from biobouncer.checks import is_id

    rows = _rows(source_db)
    schema = pa.DataFrameSchema(
        {"id": pa.Column(str, is_id(source_db, how="pattern"), nullable=True)}
    )
    # A valid-only column (with a missing cell) passes.
    valids = [row["input"] for row in rows if row["category"] == "valid"] + [None]
    schema.validate(pd.DataFrame({"id": valids}))
    # The full messy column always contains a hard invalid, so it must fail.
    with pytest.raises(pa.errors.SchemaError):
        schema.validate(pd.DataFrame({"id": _column(rows)}))


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_report_summary_matches_categories(source_db):
    rows = _cache_rows(source_db)
    categories = [row["category"] for row in rows]
    summary = bb.report(_column(rows), source_db, how="cache", version="sample").summary
    assert summary["total"] == len(rows)
    assert summary["valid"] == categories.count("valid")
    assert summary["repairable"] == categories.count("repairable")
    assert summary["invalid"] == categories.count("invalid") + categories.count(
        "repairable"
    )
    assert summary["missing"] == categories.count("missing")


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_repair_substitutes_only_the_repairable_cells(source_db):
    rows = _cache_rows(source_db)
    expected = [
        row["expect"]["suggestion"] if row["category"] == "repairable" else row["input"]
        for row in rows
    ]
    report = bb.report(_column(rows), source_db, how="cache", version="sample")
    assert report.repair() == expected


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_is_valid_id_per_row(source_db):
    rows = _cache_rows(source_db)
    verdicts = bb.is_valid_id(_column(rows), source_db, how="cache", version="sample")
    for row, verdict in zip(rows, verdicts):
        if row["category"] == "valid":
            assert verdict is True
        elif row["category"] == "missing":
            assert verdict is None
        else:
            assert verdict is False


@pytest.mark.parametrize("source_db", _CACHE_SOURCES)
def test_cache_narwhals_mask_over_the_column(source_db):
    pytest.importorskip("narwhals")
    pd = pytest.importorskip("pandas")
    from biobouncer.narwhals import valid_id_mask

    rows = _cache_rows(source_db)
    mask = list(
        valid_id_mask(
            pd.Series(_column(rows), name="id"),
            source_db,
            how="cache",
            version="sample",
        )
    )
    for row, passes in zip(rows, mask):
        assert passes == (row["category"] not in ("repairable", "invalid"))
