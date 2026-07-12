"""Cache mode: offline existence checks against a pinned snapshot of valid ids."""

from __future__ import annotations

import gzip
import os
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import platformdirs

from ._fuzzy import fuzzy_suggest
from ._pattern import _suggest, matches
from ._registry import Source, get_source


class MissingVersionError(ValueError):
    """Raised when cache mode is used without a version."""


class MissingSnapshotError(FileNotFoundError):
    """Raised when no snapshot is installed for a (source, version)."""


def cache_dir() -> Path:
    """Directory where downloaded snapshots are stored.

    Set the ``BIOGATE_CACHE_DIR`` environment variable to override the default.
    """
    override = os.environ.get("BIOGATE_CACHE_DIR")
    if override:
        return Path(override)
    return Path(platformdirs.user_cache_dir("biogate"))


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` atomically.

    Write to a temporary file in the same directory, then replace the target in
    one step with ``os.replace``. A crash or a concurrent reader never sees a
    half-written file, so a truncated snapshot or cache cannot silently report
    valid ids as invalid.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def _bundled_root():
    return files("biogate") / "_data" / "snapshots"


def _ids_from_text(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if line.strip()}


def _read_snapshot(res) -> str:
    """Read a snapshot resource, transparently decompressing a ``.gz`` file."""
    data = res.read_bytes()
    if res.name.endswith(".gz"):
        data = gzip.decompress(data)
    return data.decode("utf-8")


def _find_snapshot(source_db: str, version: str, suffix: str):
    """Locate a snapshot file, plain or gzipped, user cache before bundled.

    ``suffix`` is ``".txt"`` for the id set or ``".retired.tsv"`` for the retired
    map. Returns a path-like (a filesystem ``Path`` or a package resource) or
    ``None`` when neither form is installed.
    """
    user = cache_dir() / source_db
    for ext in (suffix, suffix + ".gz"):
        candidate = user / f"{version}{ext}"
        if candidate.is_file():
            return candidate
    bundled = _bundled_root() / source_db
    for ext in (suffix, suffix + ".gz"):
        candidate = bundled / f"{version}{ext}"
        if candidate.is_file():
            return candidate
    return None


def _strip_snapshot_ext(name: str) -> str | None:
    """Return the version for an id-snapshot filename, or ``None`` if it is not one."""
    if name.endswith(".txt.gz"):
        return name[: -len(".txt.gz")]
    if name.endswith(".txt"):
        return name[: -len(".txt")]
    return None


def _snapshot_text(source_db: str, version: str) -> str | None:
    res = _find_snapshot(source_db, version, ".txt")
    return _read_snapshot(res) if res is not None else None


def _retired_text(source_db: str, version: str) -> str | None:
    res = _find_snapshot(source_db, version, ".retired.tsv")
    return _read_snapshot(res) if res is not None else None


def _snapshot_retired(source_db: str, version: str) -> dict[str, str]:
    """Map retired id to successor from the ``<version>.retired.tsv`` sidecar.

    Each non-blank line is a retired id and its successor separated by a tab. A
    line with no successor maps to an empty string. No sidecar yields an empty
    map.
    """
    text = _retired_text(source_db, version)
    if text is None:
        return {}
    mapping: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        mapping[fields[0]] = fields[1] if len(fields) > 1 else ""
    return mapping


def _snapshot_versions(source_db: str) -> list[str]:
    versions: set[str] = set()
    user = cache_dir() / source_db
    if user.is_dir():
        for p in user.iterdir():
            version = _strip_snapshot_ext(p.name)
            if version is not None:
                versions.add(version)
    bundled = _bundled_root() / source_db
    if bundled.is_dir():
        for c in bundled.iterdir():
            version = _strip_snapshot_ext(c.name)
            if version is not None:
                versions.add(version)
    return sorted(versions)


def snapshot_set(source_db: str, version: str) -> set[str]:
    text = _snapshot_text(source_db, version)
    if text is None:
        available = _snapshot_versions(source_db)
        detail = (
            f"Installed versions: {', '.join(available)}."
            if available
            else "No snapshots are installed for this source."
        )
        raise MissingSnapshotError(
            f"No snapshot for {source_db!r} version {version!r}. {detail} "
            "Run biogate.pull() to download one."
        )
    return _ids_from_text(text)


def _fuzzy_fallback(
    s: str, fuzzy: tuple[dict[int, list[str]], int] | None
) -> str | None:
    if fuzzy is None:
        return None
    index, max_distance = fuzzy
    return fuzzy_suggest(s, index, max_distance)


def cache_check(
    source: Source,
    s: str,
    ids: set[str],
    retired: dict[str, str] | None = None,
    fuzzy: tuple[dict[int, list[str]], int] | None = None,
) -> tuple[bool, str | None, str | None]:
    """Return ``(valid, normalized, suggestion)`` for a single input.

    A well-formed id absent from ``ids`` but present in ``retired`` with a
    non-empty successor is invalid and suggests that successor. ``fuzzy`` is an
    optional ``(length index, max distance)`` pair; when set, an id with no exact,
    retired, or normalized match falls back to the nearest id within that edit
    distance.
    """
    retired = retired or {}
    if matches(source.pattern, s):
        if s in ids:
            return True, s, None
        successor = retired.get(s)
        if successor:
            return False, None, successor
        return False, None, _fuzzy_fallback(s, fuzzy)
    suggestion = _suggest(source, s)
    if suggestion is not None and suggestion in ids:
        return False, None, suggestion
    return False, None, _fuzzy_fallback(s, fuzzy)


def _snapshot_rows(base, location: str) -> list[dict]:
    rows: list[dict] = []
    if not base.is_dir():
        return rows
    for src_dir in sorted(base.iterdir(), key=lambda c: c.name):
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.iterdir(), key=lambda c: c.name):
            version = _strip_snapshot_ext(f.name)
            if version is None:
                continue
            rows.append(
                {
                    "source": src_dir.name,
                    "version": version,
                    "n_ids": len(_ids_from_text(_read_snapshot(f))),
                    "location": location,
                }
            )
    return rows


def snapshots() -> list[dict]:
    """List installed snapshots, both cached and bundled."""
    return _snapshot_rows(cache_dir(), "cache") + _snapshot_rows(
        _bundled_root(), "bundled"
    )


_USER_AGENT = "biogate/0.1 (+https://github.com/samuelbharti/biogate)"


class NoBuilderError(ValueError):
    """Raised when a source has no snapshot builder."""


def _sanitize_version(raw: str) -> str:
    raw = raw.strip().removeprefix("releases/")
    return re.sub(r"[^A-Za-z0-9._-]", "-", raw)


def parse_obo(text: str, pattern: str) -> tuple[str | None, list[str]]:
    """Extract (version, ids) from OBO text, keeping ids that match the pattern."""
    version: str | None = None
    ids: set[str] = set()
    for line in text.splitlines():
        if version is None and line.startswith("data-version:"):
            version = _sanitize_version(line[len("data-version:") :]) or None
        elif line.startswith("id:"):
            value = line[len("id:") :].strip()
            if matches(pattern, value):
                ids.add(value)
    return version, sorted(ids)


def _split_pipe(field: str) -> list[str]:
    """Split an HGNC multi-value field on ``|``, trimming quotes and spaces."""
    field = field.strip().strip('"')
    if not field:
        return []
    return [tok.strip().strip('"') for tok in field.split("|") if tok.strip()]


def parse_hgnc_tsv(
    text: str, pattern: str
) -> tuple[str | None, list[str], dict[str, str]]:
    """Extract (version, approved ids, retired map) from an HGNC complete-set TSV.

    Columns are looked up by name, never by position. The approved set is every
    ``symbol`` whose ``status`` is ``Approved`` and matches the source pattern.
    The retired map sends a previous or alias symbol to its approved successor:
    a previous symbol wins over an alias, a symbol that is itself approved is
    never retired, and an ambiguous mapping (two or more approved successors) is
    dropped. Ids and retired keys are sorted by Unicode code point so R and
    Python write byte-identical snapshots. The version is always ``None`` here
    (an HGNC snapshot is dated by its download, not by its content).
    """
    lines = text.splitlines()
    if not lines:
        return None, [], {}
    header = lines[0].split("\t")
    index = {name: i for i, name in enumerate(header)}
    if "symbol" not in index or "status" not in index:
        raise ValueError("HGNC TSV is missing the 'symbol' or 'status' column.")
    c_symbol, c_status = index["symbol"], index["status"]
    c_prev, c_alias = index.get("prev_symbol"), index.get("alias_symbol")

    approved: set[str] = set()
    prev_map: dict[str, set[str]] = {}
    alias_map: dict[str, set[str]] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) <= max(c_symbol, c_status):
            continue
        if fields[c_status].strip() != "Approved":
            continue
        symbol = fields[c_symbol].strip()
        if not symbol or not matches(pattern, symbol):
            continue
        approved.add(symbol)
        if c_prev is not None and c_prev < len(fields):
            for old in _split_pipe(fields[c_prev]):
                prev_map.setdefault(old, set()).add(symbol)
        if c_alias is not None and c_alias < len(fields):
            for old in _split_pipe(fields[c_alias]):
                alias_map.setdefault(old, set()).add(symbol)

    retired: dict[str, str] = {}
    for old in sorted(set(prev_map) | set(alias_map)):
        if not old or old in approved or not matches(pattern, old):
            continue
        targets = prev_map.get(old) or alias_map.get(old)
        if targets and len(targets) == 1:
            retired[old] = next(iter(targets))
    return None, sorted(approved), retired


@dataclass(frozen=True)
class _Builder:
    url: Callable[[Source, str | None], str]
    build: Callable[[str, Source], tuple[str | None, list[str], dict[str, str]]]


def _obo_url(source: Source, version: str | None) -> str:
    return source.cache["obo_url"]


def _obo_build(
    text: str, source: Source
) -> tuple[str | None, list[str], dict[str, str]]:
    version, ids = parse_obo(text, source.pattern)
    return version, ids, {}


def _hgnc_url(source: Source, version: str | None) -> str:
    template = source.cache["tsv_url"]
    resolved = version if version is not None else source.default_version
    return template.format(version=resolved) if "{version}" in template else template


def _hgnc_build(
    text: str, source: Source
) -> tuple[str | None, list[str], dict[str, str]]:
    return parse_hgnc_tsv(text, source.pattern)


_BUILDERS: dict[str, _Builder] = {
    "obo": _Builder(_obo_url, _obo_build),
    "hgnc_tsv": _Builder(_hgnc_url, _hgnc_build),
}


def pull(
    source_db: str, version: str | None = None, quiet: bool = False, timeout: int = 120
) -> Path:
    """Download a full snapshot for cache mode into the cache directory.

    Dispatches on the source's ``cache.builder``: ``obo`` fetches the ontology
    release, ``hgnc_tsv`` fetches the HGNC complete set. Identifiers that match
    the source pattern are written to ``cache_dir()/<source>/<version>.txt``, and
    a retired-id map, when the builder produces one, to the matching
    ``<version>.retired.tsv`` sidecar. An OBO version defaults to the ontology's
    own data-version; an HGNC version defaults to the source's ``default_version``.
    """
    source = get_source(source_db)
    cache = source.cache
    builder = _BUILDERS.get(cache.get("builder")) if cache else None
    if builder is None:
        raise NoBuilderError(f"No snapshot builder is available for {source_db!r}.")
    url = builder.url(source, version)
    if not quiet:
        print(f"Downloading {url} ...")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        text = response.read().decode("utf-8", errors="replace")
    parsed_version, ids, retired = builder.build(text, source)
    version = (
        str(version)
        if version is not None
        else (parsed_version or source.default_version)
    )
    if not version:
        raise MissingVersionError(
            f"Could not determine a version for {source_db!r}; pass version."
        )
    dest = cache_dir() / source_db / f"{version}.txt"
    _atomic_write_text(dest, "\n".join(ids) + "\n")
    if retired:
        lines = [f"{old}\t{succ}" for old, succ in sorted(retired.items())]
        _atomic_write_text(
            cache_dir() / source_db / f"{version}.retired.tsv", "\n".join(lines) + "\n"
        )
    if not quiet:
        print(f"Wrote {len(ids)} ids to {dest}")
    return dest
