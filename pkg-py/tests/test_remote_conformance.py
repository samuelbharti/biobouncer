"""Run the remote conformance corpus against vendored OLS fixtures.

The offline test replaces the network seam with a fixture reader. A live test
runs the same cases against the real API and is skipped unless opted in.
"""

import functools
import json
import os
from importlib.resources import files

import pytest

import biogate
import biogate._remote as remote


def _load_cases():
    root = files("biogate") / "_data" / "corpus" / "remote"
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
_IDS = [f"{c['source_db']}-{c['input']}" for c in CASES]


def _iter_fixture_files(root):
    for entry in root.iterdir():
        if entry.is_dir():
            yield from _iter_fixture_files(entry)
        elif entry.name.endswith(".json"):
            yield entry


@functools.cache
def _fixture_index():
    """Map each recorded fixture URL to its file, walking the tree once.

    Every fixture records the exact URL its resolver builds, so the offline
    transport is a direct lookup with no per-resolver URL parsing to keep in
    sync as sources are added.
    """
    root = files("biogate") / "_data" / "fixtures" / "remote"
    index = {}
    for path in _iter_fixture_files(root):
        record = json.loads(path.read_text(encoding="utf-8"))
        index[record["url"]] = path
    return index


def _fixture_http_get(url, timeout=30):
    """Serve the recorded fixture whose URL matches, or fail loudly."""
    path = _fixture_index().get(url)
    if path is None:
        raise AssertionError(f"missing fixture for url: {url!r}")
    fx = json.loads(path.read_text(encoding="utf-8"))
    return fx["status"], fx["body"]


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def _assert_case(case):
    expect = case["expect"]
    result = biogate.check_id(
        case["input"],
        source_db=case["source_db"],
        how="remote",
        species=case.get("species"),
    )[0]
    assert result.valid == expect["valid"]
    assert result.normalized == expect.get("normalized")
    assert result.suggestion == expect.get("suggestion")


def test_remote_corpus_is_not_empty():
    assert CASES, "no remote conformance cases were found in the vendored corpus"


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_remote_conformance_offline(case, monkeypatch):
    monkeypatch.setattr(remote, "_http_get", _fixture_http_get)
    _assert_case(case)


@pytest.mark.skipif(
    not os.environ.get("BIOGATE_REMOTE_TESTS"),
    reason="live remote tests are opt-in; set BIOGATE_REMOTE_TESTS to run them",
)
@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_remote_conformance_live(case):
    _assert_case(case)
