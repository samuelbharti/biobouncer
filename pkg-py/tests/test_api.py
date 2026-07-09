"""Behavior of the public check_id and is_valid_id functions."""

import pytest

import biogate


def test_sources_are_sorted_and_include_mondo():
    keys = biogate.sources()
    assert "mondo" in keys
    assert keys == sorted(keys)


def test_scalar_returns_one_result():
    results = biogate.check_id("MONDO:0005148", source_db="mondo")
    assert len(results) == 1
    assert results[0].valid is True
    assert results[0].normalized == "MONDO:0005148"
    assert results[0].how == "pattern"
    assert results[0].version is None


def test_vector_preserves_order_and_length():
    xs = ["MONDO:0005148", "nonsense", "mondo:5148"]
    results = biogate.check_id(xs, source_db="mondo")
    assert [r.input for r in results] == xs
    assert [r.valid for r in results] == [True, False, False]
    assert results[2].suggestion == "MONDO:0005148"


def test_species_is_echoed():
    result = biogate.check_id(
        "ENSG00000139618", source_db="ensembl", species="homo_sapiens"
    )[0]
    assert result.species == "homo_sapiens"


def test_is_valid_id_scalar_and_vector():
    assert biogate.is_valid_id("MONDO:0005148", source_db="mondo") is True
    assert biogate.is_valid_id(["MONDO:0005148", "x"], source_db="mondo") == [
        True,
        False,
    ]


def test_unknown_source_raises():
    with pytest.raises(ValueError, match="Unknown source_db"):
        biogate.check_id("x", source_db="not_a_source")


def test_unimplemented_mode_raises():
    with pytest.raises(ValueError, match="not implemented"):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="existence")


def test_invalid_mode_raises():
    with pytest.raises(ValueError, match="Invalid mode"):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="bogus")
