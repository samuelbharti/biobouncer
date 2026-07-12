"""The shared result schema: the versioned serialization contract."""

import dataclasses

from biogate import SCHEMA_VERSION
from biogate._result import Result
from biogate.schema import (
    RESULT_FIELDS,
    SUMMARY_FIELDS,
    payload,
    result_dict,
    summarize,
)


def _result(input_, valid, suggestion=None):
    return Result(
        input=input_,
        valid=valid,
        normalized=input_ if valid else None,
        suggestion=suggestion,
        source_db="mondo",
        version=None,
        species=None,
        how="pattern",
    )


def test_schema_version_is_exported_and_stable():
    assert SCHEMA_VERSION == "1"


def test_result_fields_match_the_dataclass_order():
    # The serialized field order is exactly the Result dataclass field order, so
    # a new Result field cannot silently escape the versioned schema.
    assert RESULT_FIELDS == tuple(f.name for f in dataclasses.fields(Result))


def test_result_dict_keys_are_in_schema_order():
    r = _result("MONDO:0005148", True)
    assert tuple(result_dict(r).keys()) == RESULT_FIELDS
    assert result_dict(r)["input"] == "MONDO:0005148"
    assert result_dict(r)["how"] == "pattern"


def test_summarize_counts_each_class():
    results = [
        _result("MONDO:0005148", True),
        _result("mondo:5148", False, suggestion="MONDO:0005148"),  # repairable
        _result("nope", False),  # invalid, unmappable
        _result(None, None),  # missing
    ]
    counts = summarize(results)
    assert set(counts) == set(SUMMARY_FIELDS)
    assert counts == {
        "total": 4,
        "valid": 1,
        "invalid": 2,
        "repairable": 1,
        "missing": 1,
    }
    # total is valid + invalid + missing; repairable is a subset of invalid.
    assert counts["total"] == counts["valid"] + counts["invalid"] + counts["missing"]
    assert counts["repairable"] <= counts["invalid"]


def test_payload_envelope_shape():
    env = payload([_result("MONDO:0005148", True)])
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["summary"]["total"] == 1
    assert env["results"][0]["input"] == "MONDO:0005148"
    assert tuple(env["results"][0].keys()) == RESULT_FIELDS
