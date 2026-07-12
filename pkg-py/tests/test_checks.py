"""The pandera adapter: a Check for validating columns of identifiers."""

import pytest

pytest.importorskip("pandera")

import pandas as pd  # noqa: E402
import pandera.pandas as pa  # noqa: E402

from biobouncer.checks import is_id  # noqa: E402


def _schema(**kwargs):
    return pa.DataFrameSchema({"term": pa.Column(str, is_id("mondo", **kwargs))})


def test_valid_column_passes():
    df = pd.DataFrame({"term": ["MONDO:0005148", "MONDO:0018076"]})
    validated = _schema().validate(df)
    assert list(validated["term"]) == ["MONDO:0005148", "MONDO:0018076"]


def test_invalid_column_raises():
    df = pd.DataFrame({"term": ["MONDO:0005148", "mondo:5148"]})
    with pytest.raises(pa.errors.SchemaError):
        _schema().validate(df)


def test_failure_case_reports_the_bad_value():
    df = pd.DataFrame({"term": ["MONDO:0005148", "mondo:5148"]})
    try:
        _schema().validate(df, lazy=False)
    except pa.errors.SchemaError as err:
        assert "mondo:5148" in str(err.failure_cases["failure_case"].tolist())
    else:  # pragma: no cover - the schema must fail
        pytest.fail("expected a SchemaError")


def test_null_cell_passes_when_column_is_nullable():
    # A missing cell is governed by column nullability, not flagged by the id
    # check, so a nullable column with a null value validates.
    schema = pa.DataFrameSchema({"term": pa.Column(str, is_id("mondo"), nullable=True)})
    df = pd.DataFrame({"term": ["MONDO:0005148", None]})
    validated = schema.validate(df)  # does not raise on the null cell
    assert validated["term"].iloc[0] == "MONDO:0005148"
    assert pd.isna(validated["term"].iloc[1])


def test_cache_mode_threads_through(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    schema = _schema(how="cache", version="sample")
    good = pd.DataFrame({"term": ["MONDO:0005148"]})
    assert list(schema.validate(good)["term"]) == ["MONDO:0005148"]
    bad = pd.DataFrame({"term": ["MONDO:9999999"]})
    with pytest.raises(pa.errors.SchemaError):
        schema.validate(bad)
