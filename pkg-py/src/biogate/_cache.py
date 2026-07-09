"""Cache mode: offline existence checks against a pinned snapshot of valid ids."""

from __future__ import annotations

import os
import re
import urllib.request
from importlib.resources import files
from pathlib import Path

import platformdirs

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


def _bundled_root():
    return files("biogate") / "_data" / "snapshots"


def _ids_from_text(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if line.strip()}


def _snapshot_text(source_db: str, version: str) -> str | None:
    user = cache_dir() / source_db / f"{version}.txt"
    if user.is_file():
        return user.read_text(encoding="utf-8")
    bundled = _bundled_root() / source_db / f"{version}.txt"
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    return None


def _snapshot_versions(source_db: str) -> list[str]:
    versions: set[str] = set()
    user = cache_dir() / source_db
    if user.is_dir():
        versions |= {p.stem for p in user.glob("*.txt")}
    bundled = _bundled_root() / source_db
    if bundled.is_dir():
        versions |= {c.name[:-4] for c in bundled.iterdir() if c.name.endswith(".txt")}
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


def cache_check(
    source: Source, s: str, ids: set[str]
) -> tuple[bool, str | None, str | None]:
    """Return ``(valid, normalized, suggestion)`` for a single input."""
    if matches(source.pattern, s):
        if s in ids:
            return True, s, None
        return False, None, None
    suggestion = _suggest(source, s)
    if suggestion is not None and suggestion in ids:
        return False, None, suggestion
    return False, None, None


def snapshots() -> list[dict]:
    """List installed snapshots, both cached and bundled."""
    rows: list[dict] = []
    base = cache_dir()
    if base.is_dir():
        for src_dir in sorted(base.iterdir()):
            if src_dir.is_dir():
                for f in sorted(src_dir.glob("*.txt")):
                    rows.append(
                        {
                            "source": src_dir.name,
                            "version": f.stem,
                            "n_ids": len(_ids_from_text(f.read_text(encoding="utf-8"))),
                            "location": "cache",
                        }
                    )
    bundled = _bundled_root()
    if bundled.is_dir():
        for src_dir in sorted(bundled.iterdir(), key=lambda c: c.name):
            if not src_dir.is_dir():
                continue
            txts = sorted(
                (c for c in src_dir.iterdir() if c.name.endswith(".txt")),
                key=lambda c: c.name,
            )
            for f in txts:
                rows.append(
                    {
                        "source": src_dir.name,
                        "version": f.name[:-4],
                        "n_ids": len(_ids_from_text(f.read_text(encoding="utf-8"))),
                        "location": "bundled",
                    }
                )
    return rows


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


def pull(
    source_db: str, version: str | None = None, quiet: bool = False, timeout: int = 120
) -> Path:
    """Download a full snapshot for cache mode into the cache directory.

    Fetches the source's OBO release, keeps the identifiers that match the source
    pattern, and writes them to ``cache_dir()/<source>/<version>.txt``. The
    version defaults to the ontology's own data-version.
    """
    source = get_source(source_db)
    cache = source.cache
    if not cache or cache.get("builder") != "obo":
        raise NoBuilderError(f"No snapshot builder is available for {source_db!r}.")
    url = cache["obo_url"]
    if not quiet:
        print(f"Downloading {url} ...")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        text = response.read().decode("utf-8", errors="replace")
    parsed_version, ids = parse_obo(text, source.pattern)
    version = str(version) if version is not None else parsed_version
    if not version:
        raise MissingVersionError(
            f"Could not determine a version for {source_db!r}; pass version."
        )
    dest_dir = cache_dir() / source_db
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{version}.txt"
    dest.write_text("\n".join(ids) + "\n", encoding="utf-8")
    if not quiet:
        print(f"Wrote {len(ids)} ids to {dest}")
    return dest
