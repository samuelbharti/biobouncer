"""Bounded concurrency and per-host politeness for remote checks."""

import biobouncer
import biobouncer._remote as remote


def _stub(present):
    """An OLS-style _http_get stub where only ids in ``present`` exist."""

    def _http_get(url, timeout=30):
        ident = url.split("obo_id=")[-1]
        if ident in present:
            return 200, {"page": {"totalElements": 1}}
        return 404, None

    return _http_get


def test_max_workers_reads_the_env(monkeypatch):
    monkeypatch.delenv("BIOBOUNCER_REMOTE_WORKERS", raising=False)
    assert remote._max_workers() == 1
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "8")
    assert remote._max_workers() == 8
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "0")
    assert remote._max_workers() == 1  # clamped to at least one
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "junk")
    assert remote._max_workers() == 1


def test_concurrent_resolution_preserves_order_and_verdicts(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "4")
    ids = [f"MONDO:{i:07d}" for i in range(20)]
    present = set(ids[::2])  # every other id exists
    monkeypatch.setattr(remote, "_http_get", _stub(present))
    res = biobouncer.check_id(ids, source_db="mondo", how="remote")
    assert [r.input for r in res] == ids  # completion order does not leak in
    assert [r.valid for r in res] == [r.input in present for r in res]


def test_concurrent_matches_sequential(monkeypatch, tmp_path):
    ids = [f"MONDO:{i:07d}" for i in range(12)]
    present = {ids[0], ids[3], ids[7], ids[11]}
    monkeypatch.setattr(remote, "_http_get", _stub(present))

    def _verdicts():
        return [r.valid for r in biobouncer.check_id(ids, "mondo", how="remote")]

    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path / "seq"))
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "1")
    sequential = _verdicts()
    monkeypatch.setenv("BIOBOUNCER_CACHE_DIR", str(tmp_path / "conc"))
    monkeypatch.setenv("BIOBOUNCER_REMOTE_WORKERS", "8")
    concurrent = _verdicts()
    assert sequential == concurrent


def test_ncbi_is_rate_limited_other_hosts_are_not():
    assert remote._min_interval_for("eutils.ncbi.nlm.nih.gov") > 0
    assert remote._min_interval_for("api.ncbi.nlm.nih.gov") > 0
    assert remote._min_interval_for("www.ebi.ac.uk") == 0.0


def test_ncbi_key_raises_the_rate(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    anonymous = remote._min_interval_for("eutils.ncbi.nlm.nih.gov")
    monkeypatch.setenv("NCBI_API_KEY", "secret")
    with_key = remote._min_interval_for("eutils.ncbi.nlm.nih.gov")
    assert with_key < anonymous  # a key permits more requests per second


def test_progress_is_a_noop_when_not_enabled():
    # A sequential or small or non-interactive run shows nothing.
    prog = remote._make_progress(1000, enabled=False)
    prog.update(1)
    prog.close()  # does not raise
