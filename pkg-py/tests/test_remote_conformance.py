"""Run the remote conformance corpus against vendored OLS fixtures.

The offline test replaces the network seam with a fixture reader. A live test
runs the same cases against the real API and is skipped unless opted in.
"""

import json
import os
import re
from importlib.resources import files

import pytest

import biogate
import biogate._remote as remote

_OLS_RE = re.compile(r"ontologies/([^/]+)/terms\?obo_id=(.+)$")
_ENSEMBL_RE = re.compile(r"lookup/id/([^?]+)")
_UNIPROT_RE = re.compile(r"uniprotkb/([^.?/]+)")


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


def _resolve_fixture(url):
    """Map any resolver URL to ``(resolver, subkey, ident)`` or fail loudly."""
    match = _OLS_RE.search(url)
    if match:
        return "ols", match.group(1), match.group(2)
    match = _ENSEMBL_RE.search(url)
    if match:
        return "ensembl", "id", match.group(1)
    match = _UNIPROT_RE.search(url)
    if match:
        return "uniprot", "uniprotkb", match.group(1)
    raise AssertionError(f"could not parse remote url: {url!r}")


def _fixture_http_get(url, timeout=30):
    """Serve a recorded fixture for a resolver existence URL, or fail loudly."""
    resolver, subkey, ident = _resolve_fixture(url)
    path = (
        files("biogate")
        / "_data"
        / "fixtures"
        / "remote"
        / resolver
        / subkey
        / f"{ident.replace(':', '_')}.json"
    )
    if not path.is_file():
        raise AssertionError(f"missing fixture for {resolver}/{subkey}/{ident}: {path}")
    fx = json.loads(path.read_text(encoding="utf-8"))
    return fx["status"], fx["body"]


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))


def _assert_case(case):
    expect = case["expect"]
    result = biogate.check_id(case["input"], source_db=case["source_db"], how="remote")[
        0
    ]
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
