"""Offline coverage for the snapshot builder. The network download is not tested."""

import pytest

import biogate
from biogate import NoBuilderError
from biogate._cache import parse_obo
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


def test_pull_errors_without_builder():
    with pytest.raises(NoBuilderError):
        biogate.pull("ensembl")
