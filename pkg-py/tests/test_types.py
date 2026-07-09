"""The pydantic adapter: a validating identifier type."""

import pytest

pytest.importorskip("pydantic")

from pydantic import BaseModel, ValidationError  # noqa: E402

from biogate.types import Id  # noqa: E402


def test_valid_identifier_passes():
    MondoId = Id("mondo")

    class Row(BaseModel):
        term: MondoId

    assert Row(term="MONDO:0005148").term == "MONDO:0005148"


def test_invalid_identifier_raises():
    MondoId = Id("mondo")

    class Row(BaseModel):
        term: MondoId

    with pytest.raises(ValidationError):
        Row(term="mondo:5148")


def test_cache_mode_threads_through(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))
    SampleMondo = Id("mondo", how="cache", version="sample")

    class Row(BaseModel):
        term: SampleMondo

    assert Row(term="MONDO:0005148").term == "MONDO:0005148"
    with pytest.raises(ValidationError):
        Row(term="MONDO:9999999")
