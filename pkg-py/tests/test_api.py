"""Behavior of the public check_id and is_valid_id functions."""

import pytest

import biobouncer


def test_sources_are_sorted_and_include_mondo():
    keys = biobouncer.sources()
    assert "mondo" in keys
    assert keys == sorted(keys)


def test_scalar_returns_one_result():
    results = biobouncer.check_id("MONDO:0005148", source_db="mondo")
    assert len(results) == 1
    assert results[0].valid is True
    assert results[0].normalized == "MONDO:0005148"
    assert results[0].how == "pattern"
    assert results[0].version is None


def test_vector_preserves_order_and_length():
    xs = ["MONDO:0005148", "nonsense", "mondo:5148"]
    results = biobouncer.check_id(xs, source_db="mondo")
    assert [r.input for r in results] == xs
    assert [r.valid for r in results] == [True, False, False]
    assert results[2].suggestion == "MONDO:0005148"


def test_species_is_echoed():
    result = biobouncer.check_id(
        "ENSG00000139618", source_db="ensembl", species="homo_sapiens"
    )[0]
    assert result.species == "homo_sapiens"


def test_is_valid_id_scalar_and_vector():
    assert biobouncer.is_valid_id("MONDO:0005148", source_db="mondo") is True
    assert biobouncer.is_valid_id(["MONDO:0005148", "x"], source_db="mondo") == [
        True,
        False,
    ]


def test_source_info_has_example_and_modes():
    info = {row["key"]: row for row in biobouncer.source_info()}
    assert set(info["mondo"]) == {
        "key",
        "name",
        "example",
        "modes",
        "species_aware",
        "version_aware",
    }
    assert info["mondo"]["example"] == "MONDO:0005148"
    assert info["mondo"]["modes"] == ["pattern", "cache", "remote"]
    assert info["drugbank"]["modes"] == ["pattern"]
    # hgnc supports pattern, cache (a bundled snapshot), and remote (genenames).
    assert info["hgnc"]["modes"] == ["pattern", "cache", "remote"]


def test_every_source_example_is_valid_in_pattern_mode():
    for row in biobouncer.source_info():
        assert row["example"] is not None
        assert biobouncer.is_valid_id(row["example"], source_db=row["key"]), row["key"]


def test_unknown_source_raises():
    with pytest.raises(biobouncer.UnknownSourceError, match="Unknown source_db"):
        biobouncer.check_id("x", source_db="not_a_source")


def test_invalid_mode_raises():
    with pytest.raises(biobouncer.InvalidModeError, match="Invalid mode"):
        biobouncer.check_id("MONDO:0005148", source_db="mondo", how="bogus")


def test_missing_values_propagate_as_none():
    results = biobouncer.check_id(
        [None, "MONDO:0005148", float("nan")], source_db="mondo"
    )
    assert results[0].input is None
    assert results[0].valid is None
    assert results[0].normalized is None
    assert results[0].suggestion is None
    assert results[1].valid is True
    assert results[2].valid is None


def test_is_valid_id_returns_none_for_missing():
    assert biobouncer.is_valid_id(None, source_db="mondo") is None
    assert biobouncer.is_valid_id(["MONDO:0005148", None], source_db="mondo") == [
        True,
        None,
    ]


def test_empty_input_returns_empty_list():
    assert biobouncer.check_id([], source_db="mondo") == []


def test_rejects_unsupported_input_types():
    with pytest.raises(TypeError):
        biobouncer.check_id({"MONDO:0005148": 1}, source_db="mondo")
    with pytest.raises(TypeError):
        biobouncer.check_id(b"MONDO:0005148", source_db="mondo")


def test_rejects_non_string_source_db():
    with pytest.raises(TypeError):
        biobouncer.check_id("x", source_db=1)
    with pytest.raises(TypeError):
        biobouncer.check_id("x", source_db=["mondo", "efo"])
