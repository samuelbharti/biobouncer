"""Offline, species-aware validation for Ensembl in pattern mode."""

import biobouncer
from biobouncer._pattern import _ensembl_id_prefix

HUMAN = "ENSG00000139618"
MOUSE = "ENSMUSG00000059552"
RAT = "ENSRNOG00000010756"


def _check(ident, species, source_db="ensembl"):
    return biobouncer.check_id(
        ident, source_db=source_db, how="pattern", species=species
    )[0]


def test_human_id_with_human_species_is_valid():
    res = _check(HUMAN, "homo_sapiens")
    assert res.valid is True
    assert res.normalized == HUMAN
    assert res.suggestion is None


def test_mouse_id_with_human_species_is_invalid():
    res = _check(MOUSE, "homo_sapiens")
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_human_id_with_taxon_species_is_valid():
    res = _check(HUMAN, 9606)
    assert res.valid is True
    assert res.normalized == HUMAN


def test_unknown_species_is_lenient():
    res = _check(HUMAN, "platypus")
    assert res.valid is True
    assert res.normalized == HUMAN


def test_lowercase_mouse_id_suggests_when_species_matches():
    res = _check(MOUSE.lower(), "mus_musculus")
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion == MOUSE


def test_lowercase_mouse_id_no_suggestion_when_species_mismatches():
    res = _check(MOUSE.lower(), "homo_sapiens")
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_rat_id_with_human_species_is_invalid():
    res = _check(RAT, "homo_sapiens")
    assert res.valid is False
    assert res.normalized is None
    assert res.suggestion is None


def test_lowercase_rat_id_suggests_when_species_matches():
    res = _check(RAT.lower(), "rattus_norvegicus")
    assert res.valid is False
    assert res.suggestion == RAT


def test_non_species_aware_source_ignores_species():
    res = _check("MONDO:0005148", "homo_sapiens", source_db="mondo")
    assert res.valid is True
    assert res.normalized == "MONDO:0005148"


def test_ensembl_id_prefix_extraction():
    assert _ensembl_id_prefix("ENSG00000139618") == ""
    assert _ensembl_id_prefix("ENSMUSG00000059552") == "MUS"
    assert _ensembl_id_prefix("ENSRNOG00000010756") == "RNO"
    assert _ensembl_id_prefix("MONDO:0005148") is None
