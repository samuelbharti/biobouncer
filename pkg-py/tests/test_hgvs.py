"""HGVS is a grammar source: pattern mode checks variant syntax only.

The full grammar is exercised by the shared conformance corpus; these are
focused checks on representative shapes and on the pattern-only contract.
"""

import pytest

import biobouncer
from biobouncer import MissingSnapshotError

VALID = [
    "NM_004006.2:c.4375C>T",
    "NC_000023.11:g.32867861_32867862del",
    "NM_004006.2:c.88+1G>T",
    "NM_004006.2:c.76_77insACGT",
    "NM_004006.2:c.112_117delinsTG",
    "NP_003997.1:p.(Gly56Ala)",
    "NP_003997.1:p.Trp26Ter",
    "NP_003997.1:p.Arg97ProfsTer23",
]

INVALID = [
    "c.4375C>T",  # no reference sequence
    "NM_004006.2:c.4375C>",  # missing alternate base
    "NM_004006.2:x.123A>T",  # unknown coordinate type
    "NM_004006.2:c.76insG",  # insertion needs a range
    "NM_004006.2:p.Gly56Xyz",  # unknown amino acid code
]


@pytest.mark.parametrize("variant", VALID)
def test_well_formed_variants_are_valid(variant):
    assert biobouncer.is_valid_id(variant, "hgvs") is True


@pytest.mark.parametrize("variant", INVALID)
def test_malformed_variants_are_invalid(variant):
    assert biobouncer.is_valid_id(variant, "hgvs") is False


def test_hgvs_cache_mode_has_no_snapshot(tmp_path, monkeypatch):
    # hgvs supports pattern (syntax) and remote (Mutalyzer) modes. It ships no
    # cache snapshot, so cache mode reports the missing snapshot explicitly.
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    with pytest.raises(MissingSnapshotError):
        biobouncer.check_id(
            "NM_004006.2:c.4375C>T", "hgvs", how="cache", version="sample"
        )
