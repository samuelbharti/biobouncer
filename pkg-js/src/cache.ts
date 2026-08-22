// Cache mode: offline existence against a bundled or user-cache snapshot. Ported
// from pkg-py/src/biobouncer/_cache.py. Node-only (filesystem and gzip).

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";
import { InvalidVersionError, MissingSnapshotError } from "./errors";
import { type FuzzyIndex, fuzzyIndex, fuzzySuggest } from "./fuzzy";
import { matches, suggest } from "./pattern";
import type { SourceSpec } from "./registry";

// Snapshots ship beside this module: src/_data/snapshots in dev, dist/_data/snapshots
// in the published build.
const BUNDLED = fileURLToPath(new URL("./_data/snapshots", import.meta.url));

/** Fuzzy configuration resolved once per batch. */
export interface FuzzyConfig {
  index: FuzzyIndex;
  maxDistance: number;
  ignoreCase: boolean;
}

function userCacheDir(app: string): string {
  const home = homedir();
  if (process.platform === "win32") {
    const base = process.env.LOCALAPPDATA ?? join(home, "AppData", "Local");
    return join(base, app, "Cache");
  }
  if (process.platform === "darwin") {
    return join(home, "Library", "Caches", app);
  }
  const base = process.env.XDG_CACHE_HOME ?? join(home, ".cache");
  return join(base, app);
}

/** The snapshot cache directory: BIOBOUNCER_CACHE_DIR, else the platform default. */
export function cacheDir(): string {
  return process.env.BIOBOUNCER_CACHE_DIR || userCacheDir("biobouncer");
}

function validateVersion(version: string): void {
  if (
    version === "" ||
    version.includes("/") ||
    version.includes("\\") ||
    version.includes("..")
  ) {
    throw new InvalidVersionError(`invalid version: ${version}`);
  }
}

interface SnapshotHit {
  path: string;
  gz: boolean;
}

function findSnapshot(
  source: string,
  version: string,
  suffix: string,
): SnapshotHit | null {
  validateVersion(version);
  const dirs = [cacheDir(), BUNDLED];
  for (const dir of dirs) {
    const plain = join(dir, source, `${version}${suffix}`);
    if (existsSync(plain)) return { path: plain, gz: false };
    const gz = `${plain}.gz`;
    if (existsSync(gz)) return { path: gz, gz: true };
  }
  return null;
}

function readSnapshot(hit: SnapshotHit): string {
  const buf = readFileSync(hit.path);
  return (hit.gz ? gunzipSync(buf) : buf).toString("utf8");
}

function idsFromText(text: string): Set<string> {
  const out = new Set<string>();
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (t) out.add(t);
  }
  return out;
}

/** Whether a `.txt` snapshot for `source`/`version` is installed. */
export function hasSnapshot(source: string, version: string): boolean {
  return findSnapshot(source, version, ".txt") !== null;
}

/** The set of canonical ids in a snapshot, or throw MissingSnapshotError. */
export function snapshotSet(source: string, version: string): Set<string> {
  const hit = findSnapshot(source, version, ".txt");
  if (hit === null) {
    throw new MissingSnapshotError(`no ${source} snapshot for version ${version}`);
  }
  return idsFromText(readSnapshot(hit));
}

/** The retired-id -> successor map for a snapshot ("" successor when unknown). */
export function snapshotRetired(source: string, version: string): Map<string, string> {
  const map = new Map<string, string>();
  const hit = findSnapshot(source, version, ".retired.tsv");
  if (hit === null) return map;
  for (const line of readSnapshot(hit).split(/\r?\n/)) {
    if (!line.trim()) continue;
    const fields = line.split("\t");
    const retired = fields[0];
    if (retired === undefined) continue;
    map.set(retired, fields.length > 1 ? (fields[1] ?? "") : "");
  }
  return map;
}

function versionsIn(dir: string, source: string): string[] {
  const base = join(dir, source);
  if (!existsSync(base)) return [];
  const versions = new Set<string>();
  for (const name of readdirSync(base)) {
    if (name.includes(".retired.")) continue;
    const m = /^(.+?)\.txt(?:\.gz)?$/.exec(name);
    if (m?.[1]) versions.add(m[1]);
  }
  return [...versions];
}

/** Installed versions for a source, across the cache dir and bundled snapshots. */
export function installedVersions(source: string): string[] {
  const all = new Set<string>([
    ...versionsIn(cacheDir(), source),
    ...versionsIn(BUNDLED, source),
  ]);
  return [...all].sort();
}

/** The version to use when a caller omits one: pinned default, newest date, or sample. */
export function defaultCacheVersion(source: string, spec: SourceSpec): string | null {
  const pinned = spec.default_version;
  if (pinned && hasSnapshot(source, pinned)) return pinned;
  const dated = installedVersions(source).filter((v) => v !== "sample");
  if (dated.length > 0) return dated[dated.length - 1] ?? null;
  if (hasSnapshot(source, "sample")) return "sample";
  return null;
}

/** Build the fuzzy config for a source, or null when it declares no fuzzy suggest. */
export function buildFuzzy(spec: SourceSpec, ids: Set<string>): FuzzyConfig | null {
  const s = spec.suggest;
  if (!s) return null;
  if (!s.fuzzy) return null;
  return {
    index: fuzzyIndex(ids),
    maxDistance: s.fuzzy.max_distance,
    ignoreCase: Boolean(s.case_insensitive),
  };
}

export interface CacheVerdict {
  valid: boolean;
  normalized: string | null;
  suggestion: string | null;
}

/** The cache-mode verdict for a single input. */
export function cacheCheck(
  spec: SourceSpec,
  s: string,
  ids: Set<string>,
  retired: Map<string, string>,
  fuzzy: FuzzyConfig | null,
): CacheVerdict {
  const fuzzyFallback = (): string | null =>
    fuzzy ? fuzzySuggest(s, fuzzy.index, fuzzy.maxDistance, fuzzy.ignoreCase) : null;

  if (matches(spec.pattern, s)) {
    if (ids.has(s)) return { valid: true, normalized: s, suggestion: null };
    const successor = retired.get(s);
    if (successor) return { valid: false, normalized: null, suggestion: successor };
    return { valid: false, normalized: null, suggestion: fuzzyFallback() };
  }
  const repaired = suggest(spec, s);
  if (repaired !== null && ids.has(repaired)) {
    return { valid: false, normalized: null, suggestion: repaired };
  }
  return { valid: false, normalized: null, suggestion: fuzzyFallback() };
}

export interface SnapshotRow {
  source: string;
  version: string;
  nIds: number;
  location: "cache" | "bundled";
}

/** Every installed snapshot, from the cache dir and the bundled set. */
export function snapshots(): SnapshotRow[] {
  const rows: SnapshotRow[] = [];
  const scan = (dir: string, location: "cache" | "bundled"): void => {
    if (!existsSync(dir)) return;
    for (const source of readdirSync(dir)) {
      for (const version of versionsIn(dir, source)) {
        const hit = findSnapshot(source, version, ".txt");
        if (hit === null) continue;
        rows.push({
          source,
          version,
          nIds: idsFromText(readSnapshot(hit)).size,
          location,
        });
      }
    }
  };
  scan(cacheDir(), "cache");
  scan(BUNDLED, "bundled");
  return rows;
}
