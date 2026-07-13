"""Run the shared cross-language conformance corpus against the Python package."""

import json
from importlib.resources import files

import pytest

import biobouncer


def _load_cases():
    root = files("biobouncer") / "_data" / "corpus"
    cases = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not entry.name.endswith(".jsonl"):
            continue
        for line in entry.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


CASES = _load_cases()


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    # Empty cache dir, so cache cases resolve to the bundled sample snapshot.
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))


def test_corpus_is_not_empty():
    assert CASES, "no conformance cases were found in the vendored corpus"


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{c['source_db']}-{c['how']}-{c['input']}" for c in CASES]
)
def test_conformance(case):
    expect = case["expect"]
    result = biobouncer.check_id(
        case["input"],
        source_db=case["source_db"],
        how=case["how"],
        species=case.get("species"),
        version=case.get("version"),
    )[0]
    assert result.valid == expect["valid"]
    assert result.normalized == expect.get("normalized")
    assert result.suggestion == expect.get("suggestion")
