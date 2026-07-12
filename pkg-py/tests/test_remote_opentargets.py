"""The Open Targets resolver: the first GraphQL (POST) remote check."""

import json

import biobouncer
import biobouncer._remote as remote


def _stub(covered):
    """A GraphQL _http_post stub: ids in ``covered`` resolve to a target."""

    def _http_post(url, data, timeout=30):
        assert url.endswith("/graphql")
        ident = json.loads(data)["variables"]["ensemblId"]
        target = {"id": ident} if ident in covered else None
        return 200, {"data": {"target": target}}

    return _http_post


def test_covered_target_is_valid(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_post", _stub({"ENSG00000139618"}))
    res = biobouncer.check_id("ENSG00000139618", source_db="opentargets", how="remote")[
        0
    ]
    assert res.valid is True
    assert res.normalized == "ENSG00000139618"


def test_uncovered_gene_is_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_post", _stub(set()))
    res = biobouncer.check_id("ENSG00000000000", source_db="opentargets", how="remote")[
        0
    ]
    assert res.valid is False


def test_malformed_case_suggests_the_covered_form(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(remote, "_http_post", _stub({"ENSG00000139618"}))
    res = biobouncer.check_id("ensg00000139618", source_db="opentargets", how="remote")[
        0
    ]
    assert res.valid is False
    assert res.suggestion == "ENSG00000139618"


def test_body_carries_the_graphql_query_and_id():
    body = remote._opentargets_body(None, "ENSG00000139618")
    payload = json.loads(body)
    assert "target(ensemblId:" in payload["query"]
    assert payload["variables"] == {"ensemblId": "ENSG00000139618"}


def test_unexpected_status_is_indeterminate(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))

    def _boom(url, data, timeout=30):
        return 500, None

    monkeypatch.setattr(remote, "_http_post", _boom)
    res = biobouncer.check_id(
        "ENSG00000139618",
        source_db="opentargets",
        how="remote",
        on_error="indeterminate",
    )[0]
    assert res.valid is None
    assert res.error is not None


def test_opentargets_is_a_registered_source():
    info = {row["key"]: row for row in biobouncer.source_info()}
    assert "opentargets" in info
    assert info["opentargets"]["modes"] == ["pattern", "remote"]
