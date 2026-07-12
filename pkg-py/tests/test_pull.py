"""Offline coverage for the snapshot builder. The network download is not tested."""

import pytest

import biogate
from biogate import NoBuilderError
from biogate._cache import parse_hgnc_tsv, parse_obo
from biogate._registry import get_source


def test_parse_obo_extracts_version_and_only_matching_ids():
    text = "\n".join(
        [
            "format-version: 1.2",
            "data-version: releases/2026-07-06",
            "",
            "[Term]",
            "id: MONDO:0005148",
            "name: type 2 diabetes mellitus",
            "",
            "[Term]",
            "id: MONDO:0007739",
            "",
            "[Typedef]",
            "id: RO:0002211",
        ]
    )
    version, ids = parse_obo(text, get_source("mondo").pattern)
    assert version == "2026-07-06"
    assert ids == ["MONDO:0005148", "MONDO:0007739"]


def test_parse_hgnc_tsv_extracts_approved_and_retired():
    header = "\t".join(["symbol", "status", "prev_symbol", "alias_symbol"])
    rows = [
        "TP53\tApproved\t\tP53",
        "KMT2A\tApproved\tMLL\tMLL1|ALL-1",
        "KMT2D\tApproved\tMLL2|MLL4\t",
        "EGFR\tEntry Withdrawn\t\t",  # withdrawn, excluded from the approved set
        "CARS1\tApproved\tCARS\t",
        "FOO\tApproved\tSHARED\t",  # SHARED maps to two genes, so it is dropped
        "BAR\tApproved\tSHARED\t",
        "BAZ\tApproved\tTP53\t",  # TP53 is approved, so it is never retired
        "GENEA\tApproved\tOLD1\t",  # a previous symbol wins over an alias
        "GENEB\tApproved\t\tOLD1",
    ]
    version, ids, retired = parse_hgnc_tsv(
        "\n".join([header, *rows]), get_source("hgnc").pattern
    )
    assert version is None
    assert ids == [
        "BAR",
        "BAZ",
        "CARS1",
        "FOO",
        "GENEA",
        "GENEB",
        "KMT2A",
        "KMT2D",
        "TP53",
    ]
    assert retired == {
        "ALL-1": "KMT2A",
        "CARS": "CARS1",
        "MLL": "KMT2A",
        "MLL1": "KMT2A",
        "MLL2": "KMT2D",
        "MLL4": "KMT2D",
        "OLD1": "GENEA",
        "P53": "TP53",
    }


def test_pull_errors_without_builder():
    with pytest.raises(NoBuilderError):
        biogate.pull("ensembl")


def test_pull_errors_for_a_bundled_only_source():
    # hgnc has a cache block, so it offers cache mode, but no download builder, so
    # pull must still refuse rather than pretend it can refresh the snapshot.
    with pytest.raises(NoBuilderError):
        biogate.pull("hgnc")
