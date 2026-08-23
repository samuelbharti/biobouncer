// Filesystem and environment seam (browser stub).
//
// The browser build aliases "./io" to this file (see tsup.browser.config.ts), so
// nothing in the browser bundle imports node:fs, node:zlib, or friends. There is
// no filesystem here: cache mode and pull are Node-only and degrade cleanly, while
// pattern mode (pure logic) and remote mode (fetch) work unchanged. The remote
// on-disk response cache simply turns into a no-op, so every remote check goes to
// the network.

/** True when a real filesystem is available (never, in the browser). */
export const HAS_FS = false;

/** No bundled snapshots without a filesystem. */
export function bundledSnapshotsDir(): string {
  return "";
}

/** A nominal cache path; nothing is read from or written to it in the browser. */
export function cacheBaseDir(): string {
  return "/biobouncer-cache";
}

/** Environment variables are not available in the browser. */
export function env(_name: string): string | undefined {
  return undefined;
}

/** Nothing exists on a filesystem that is not there. */
export function existsSync(_path: string): boolean {
  return false;
}

/** No directories to list without a filesystem. */
export function readdir(_path: string): string[] {
  return [];
}

/** Reachable only after existsSync, which is always false here, so this never runs. */
export function readText(_path: string, _gz: boolean): string {
  throw new Error("filesystem access is not available in the browser");
}

/** No files to read; the remote cache is always a miss in the browser. */
export function readTextIfExists(_path: string): string | null {
  return null;
}

/** Writes are dropped: the remote on-disk cache is a no-op in the browser. */
export function writeTextEnsuringDir(_path: string, _data: string): void {
  // no-op
}

/** Join path segments with "/", collapsing redundant separators. */
export function join(...parts: string[]): string {
  return parts
    .filter((p) => p !== "")
    .join("/")
    .replace(/\/{2,}/g, "/");
}
