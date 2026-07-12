"""The validate-and-repair report: the 'clean my column' entry point."""

import pytest

import biogate as bg

# A fixed hgnc column exercised across backends: one valid, one repairable
# (retired to a successor), one unmappable, one missing.
_COLUMN = ["TP53", "MLL", "ZZZZZZZZZZ", None]
_REPAIRED = ["TP53", "KMT2A", "ZZZZZZZZZZ", None]


def test_report_from_a_list_needs_no_frame_dependency():
    rep = bg.report(_COLUMN, "hgnc", how="cache")
    assert len(rep) == 4
    assert rep.source_db == "hgnc"
    assert rep.how == "cache"
    assert [r.input for r in rep.results] == _COLUMN
    assert rep.summary == {
        "total": 4,
        "valid": 1,
        "invalid": 2,
        "repairable": 1,
        "missing": 1,
        "indeterminate": 0,
    }
    assert "1 repairable" in repr(rep)


def test_repair_substitutes_only_fixable_values():
    rep = bg.report(_COLUMN, "hgnc", how="cache")
    # valid kept, retired -> successor, unmappable kept, missing kept.
    assert rep.repair() == _REPAIRED


def test_to_frame_defaults_to_pandas_for_a_list():
    pytest.importorskip("narwhals")
    pd = pytest.importorskip("pandas")
    frame = bg.report(_COLUMN, "hgnc", how="cache").to_frame()
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "input",
        "valid",
        "normalized",
        "suggestion",
        "error",
    ]
    assert frame["suggestion"].iloc[1] == "KMT2A"
    assert bool(frame["valid"].iloc[0]) is True


def test_pandas_series_round_trips_to_pandas():
    pytest.importorskip("narwhals")
    pd = pytest.importorskip("pandas")
    s = pd.Series(_COLUMN, name="gene")
    rep = bg.report(s, "hgnc", how="cache")
    repaired = rep.repair()
    assert isinstance(repaired, pd.Series)
    assert repaired.name == "gene"
    assert repaired.iloc[1] == "KMT2A"
    assert pd.isna(repaired.iloc[3])
    assert isinstance(rep.to_frame(), pd.DataFrame)


def test_polars_series_round_trips_to_polars():
    pytest.importorskip("narwhals")
    pl = pytest.importorskip("polars")
    s = pl.Series("gene", _COLUMN)
    rep = bg.report(s, "hgnc", how="cache")
    repaired = rep.repair()
    assert isinstance(repaired, pl.Series)
    assert repaired.to_list() == _REPAIRED


def test_report_threads_pattern_mode_and_species():
    # pattern mode over a plain list needs no snapshot and no network.
    rep = bg.report(["MONDO:0005148", "mondo:5148"], "mondo")
    assert [r.valid for r in rep.results] == [True, False]
    assert rep.repair() == ["MONDO:0005148", "MONDO:0005148"]
