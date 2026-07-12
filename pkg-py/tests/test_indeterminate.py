"""on_error='indeterminate': one unreachable id does not sink the batch."""

import pytest

import biogate
import biogate._remote as remote


def test_default_raises_on_a_remote_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))

    def _boom(url, timeout=30):
        raise remote.RemoteError("connection refused")

    monkeypatch.setattr(remote, "_http_get", _boom)
    with pytest.raises(remote.RemoteError):
        biogate.check_id("MONDO:0005148", source_db="mondo", how="remote")


def test_indeterminate_isolates_the_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))

    # One id resolves, the other always fails: the good one is still checked.
    def _mixed(url, timeout=30):
        if "obo_id=MONDO:0005148" in url:
            return 200, {"page": {"totalElements": 1}}
        raise remote.RemoteError("connection refused")

    monkeypatch.setattr(remote, "_http_get", _mixed)
    res = biogate.check_id(
        ["MONDO:0005148", "MONDO:0000001"],
        source_db="mondo",
        how="remote",
        on_error="indeterminate",
    )
    assert res[0].valid is True
    assert res[0].error is None
    # The unreachable id is indeterminate: valid None with a reason, not False.
    assert res[1].valid is None
    assert res[1].error is not None
    assert "connection refused" in res[1].error


def test_indeterminate_does_not_cache_the_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))
    calls = {"n": 0}

    def _boom(url, timeout=30):
        calls["n"] += 1
        raise remote.RemoteError("connection refused")

    monkeypatch.setattr(remote, "_http_get", _boom)
    biogate.check_id("MONDO:0005148", "mondo", how="remote", on_error="indeterminate")
    biogate.check_id("MONDO:0005148", "mondo", how="remote", on_error="indeterminate")
    # A second run refetches, so the failure was never persisted as a verdict.
    assert calls["n"] == 2


def test_malformed_input_is_invalid_not_indeterminate(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))

    def _boom(url, timeout=30):
        raise remote.RemoteError("connection refused")

    monkeypatch.setattr(remote, "_http_get", _boom)
    # "mondo:5148" is malformed; it is invalid regardless of the network, and its
    # suggestion just cannot be confirmed, so it is not indeterminate.
    res = biogate.check_id(
        "mondo:5148", source_db="mondo", how="remote", on_error="indeterminate"
    )[0]
    assert res.valid is False
    assert res.error is None


def test_invalid_on_error_rejected():
    with pytest.raises(ValueError, match="on_error"):
        biogate.check_id("MONDO:0005148", "mondo", on_error="nonsense")
