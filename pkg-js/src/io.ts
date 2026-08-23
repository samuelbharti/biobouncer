// Filesystem and environment seam (Node implementation).
//
// cache.ts and remote.ts reach the disk and the environment only through this
// module. The browser build swaps it for io.browser.ts (a filesystem-free stub),
// which is how the package bundles for the browser without pulling in node:fs and
// friends. Keep this file the only place in the runtime graph that imports node
// builtins.

import {
  existsSync as fsExists,
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname as pathDirname, join as pathJoin } from "node:path";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";

/** True when a real filesystem is available (always, in Node). */
export const HAS_FS = true;

/** Absolute path to the snapshots that ship beside the built package. */
export function bundledSnapshotsDir(): string {
  return fileURLToPath(new URL("./_data/snapshots", import.meta.url));
}

/** The snapshot cache directory: BIOBOUNCER_CACHE_DIR, else the platform default. */
export function cacheBaseDir(): string {
  const override = process.env.BIOBOUNCER_CACHE_DIR;
  if (override) return override;
  const app = "biobouncer";
  const home = homedir();
  if (process.platform === "win32") {
    const base = process.env.LOCALAPPDATA ?? pathJoin(home, "AppData", "Local");
    return pathJoin(base, app, "Cache");
  }
  if (process.platform === "darwin") {
    return pathJoin(home, "Library", "Caches", app);
  }
  const base = process.env.XDG_CACHE_HOME ?? pathJoin(home, ".cache");
  return pathJoin(base, app);
}

/** Read an environment variable, or undefined when it is not set. */
export function env(name: string): string | undefined {
  return process.env[name];
}

/** Whether a file exists. */
export function existsSync(path: string): boolean {
  return fsExists(path);
}

/** Directory entries, or [] when the directory does not exist. */
export function readdir(path: string): string[] {
  if (!fsExists(path)) return [];
  return readdirSync(path);
}

/** Read a text file, gunzipping first when `gz` is set. */
export function readText(path: string, gz: boolean): string {
  const buf = readFileSync(path);
  return (gz ? gunzipSync(buf) : buf).toString("utf8");
}

/** Read a text file if it exists, else null. Never throws on a missing file. */
export function readTextIfExists(path: string): string | null {
  if (!fsExists(path)) return null;
  return readFileSync(path, "utf8");
}

/** Write text, creating the parent directory first. */
export function writeTextEnsuringDir(path: string, data: string): void {
  mkdirSync(pathDirname(path), { recursive: true });
  writeFileSync(path, data);
}

/** Join path segments. */
export function join(...parts: string[]): string {
  return pathJoin(...parts);
}
