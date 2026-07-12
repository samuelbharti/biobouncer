"""Behavior of the biogate command-line interface."""

import json

import pytest

from biogate.cli import main


def test_check_all_valid_exits_zero(capsys):
    code = main(["check", "-s", "mondo", "MONDO:0005148", "MONDO:0018076"])
    assert code == 0
    out = capsys.readouterr().out
    assert "MONDO:0005148" in out


def test_check_with_invalid_exits_one(capsys):
    code = main(["check", "-s", "mondo", "MONDO:0005148", "mondo:5148"])
    assert code == 1
    captured = capsys.readouterr()
    assert "FAIL" in captured.out
    assert "did you mean MONDO:0005148" in captured.out
    assert "1 of 2 invalid" in captured.err


def test_check_json_format(capsys):
    code = main(["check", "-s", "mondo", "--format", "json", "-q", "mondo:5148"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["input"] == "mondo:5148"
    assert payload[0]["valid"] is False
    assert payload[0]["suggestion"] == "MONDO:0005148"


def test_check_invalid_only(capsys):
    code = main(
        ["check", "-s", "mondo", "--invalid-only", "-q", "MONDO:0005148", "mondo:5148"]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "mondo:5148" in out
    assert "MONDO:0005148\n" not in out  # the valid one is not printed


def test_check_reads_file(tmp_path, capsys):
    path = tmp_path / "ids.txt"
    path.write_text("MONDO:0005148\n\nmondo:5148\n", encoding="utf-8")
    code = main(["check", "-s", "mondo", "-f", str(path)])
    assert code == 1
    assert "1 of 2 invalid" in capsys.readouterr().err


def test_check_no_ids_exits_two(capsys):
    # No positional ids and stdin is a captured non-readable stream in pytest.
    code = main(["check", "-s", "mondo"])
    assert code == 2
    assert "no identifiers" in capsys.readouterr().err


def test_check_unknown_source_exits_two(capsys):
    code = main(["check", "-s", "not_a_source", "X"])
    assert code == 2
    assert "Unknown source_db" in capsys.readouterr().err


def test_sources_lists_keys(capsys):
    code = main(["sources"])
    assert code == 0
    keys = capsys.readouterr().out.split()
    assert "mondo" in keys
    assert keys == sorted(keys)


def test_info_json_for_one_source(capsys):
    code = main(["info", "-s", "mondo", "--format", "json"])
    assert code == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["key"] == "mondo"
    assert rows[0]["example"] == "MONDO:0005148"
    assert rows[0]["modes"] == ["pattern", "cache", "remote"]


def test_info_unknown_source_exits_two(capsys):
    code = main(["info", "-s", "not_a_source"])
    assert code == 2


def test_missing_subcommand_errors():
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_refresh_flag_threads_to_the_core(monkeypatch):
    seen = {}

    def _fake_check_id(ids, source_db, how, species, version, refresh):
        seen["refresh"] = refresh
        return []

    monkeypatch.setattr("biogate.cli.check_id", _fake_check_id)
    main(["check", "-s", "mondo", "--how", "remote", "--refresh", "X"])
    assert seen["refresh"] is True
    main(["check", "-s", "mondo", "--how", "remote", "X"])
    assert seen["refresh"] is False


def test_remote_mode_all_valid_exits_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))
    import biogate._remote as remote

    def _present(url, timeout=30):
        return 200, {"page": {"totalElements": 1}}

    monkeypatch.setattr(remote, "_http_get", _present)
    code = main(["check", "-s", "mondo", "--how", "remote", "-q", "MONDO:0005148"])
    assert code == 0


def test_remote_network_failure_exits_three(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BIOGATE_CACHE_DIR", str(tmp_path))
    import biogate._remote as remote

    def _boom(url, timeout=30):
        raise remote.RemoteError("connection refused")

    monkeypatch.setattr(remote, "_http_get", _boom)
    code = main(["check", "-s", "mondo", "--how", "remote", "MONDO:0005148"])
    assert code == 3  # distinct from 1 (some invalid) and 2 (usage)
    assert "biogate: connection refused" in capsys.readouterr().err
