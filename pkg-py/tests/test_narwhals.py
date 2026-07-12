"""The narwhals adapter: one column check across pandas, polars, and pyarrow."""

import pytest

pytest.importorskip("narwhals")
pd = pytest.importorskip("pandas")

from biobouncer.narwhals import valid_id_mask  # noqa: E402


def test_pandas_column():
    s = pd.Series(["MONDO:0005148", "mondo:5148", "nonsense"], name="term")
    mask = valid_id_mask(s, "mondo")
    assert list(mask) == [True, False, False]


def test_polars_column():
    pl = pytest.importorskip("polars")
    s = pl.Series("term", ["MONDO:0005148", "mondo:5148"])
    mask = valid_id_mask(s, "mondo")
    assert mask.to_list() == [True, False]


def test_pyarrow_column():
    pa = pytest.importorskip("pyarrow")
    arr = pa.chunked_array([["MONDO:0005148", "mondo:5148"]])
    mask = valid_id_mask(arr, "mondo")
    assert mask.to_pylist() == [True, False]


def test_null_cell_is_missing_not_invalid():
    # A missing cell is not a failed identifier, so the mask keeps it True; only
    # the malformed value is False. This must hold even in pandas, where a null in
    # a string column reads back as a float NaN.
    s = pd.Series(["MONDO:0005148", None, "nonsense"], name="term")
    mask = valid_id_mask(s, "mondo")
    assert list(mask) == [True, True, False]


def test_cache_mode_threads_through(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    s = pd.Series(["MONDO:0005148", "MONDO:9999999"], name="term")
    mask = valid_id_mask(s, "mondo", how="cache", version="sample")
    assert list(mask) == [True, False]
