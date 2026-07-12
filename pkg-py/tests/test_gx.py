"""The Great Expectations expectation. Skipped when GX is not installed."""

import pytest

pytest.importorskip("great_expectations")
pd = pytest.importorskip("pandas")

import great_expectations as gx  # noqa: E402

from biobouncer.gx import ExpectColumnValuesToBeValidId  # noqa: E402


def _batch(df):
    context = gx.get_context(mode="ephemeral")
    return (
        context.data_sources.add_pandas("p")
        .add_dataframe_asset("a")
        .add_batch_definition_whole_dataframe("b")
        .get_batch(batch_parameters={"dataframe": df})
    )


def test_all_valid_column_succeeds():
    df = pd.DataFrame({"term": ["MONDO:0005148", "MONDO:0018076"]})
    result = _batch(df).validate(
        ExpectColumnValuesToBeValidId(column="term", source_db="mondo")
    )
    assert result.success is True


def test_invalid_value_fails_and_is_counted():
    df = pd.DataFrame({"term": ["MONDO:0005148", "mondo:5148", "MONDO:0018076"]})
    result = _batch(df).validate(
        ExpectColumnValuesToBeValidId(column="term", source_db="mondo")
    )
    assert result.success is False
    assert result.result["unexpected_percent"] == pytest.approx(100 / 3)


def test_null_cell_is_not_counted_as_invalid():
    # A missing value is not a failed identifier; it must not count as unexpected.
    df = pd.DataFrame({"term": ["MONDO:0005148", None, "MONDO:0018076"]})
    result = _batch(df).validate(
        ExpectColumnValuesToBeValidId(column="term", source_db="mondo")
    )
    assert result.success is True


def test_mostly_tolerates_some_invalid():
    df = pd.DataFrame({"term": ["MONDO:0005148", "mondo:5148", "MONDO:0018076"]})
    result = _batch(df).validate(
        ExpectColumnValuesToBeValidId(column="term", source_db="mondo", mostly=0.5)
    )
    assert result.success is True
