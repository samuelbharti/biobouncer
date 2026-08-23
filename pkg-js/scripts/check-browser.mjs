// Verify the browser bundle is actually browser-safe: no node builtins survive in
// the output, and the filesystem-free seam behaves. Run after build, when
// dist/browser exists. The platform:browser build already fails on a stray
// node:fs import, so this is a second, explicit guard with a clear message.

import { readFileSync } from "node:fs";

const ESM = new URL("../dist/browser/index.js", import.meta.url);
const CJS = new URL("../dist/browser/index.cjs", import.meta.url);

const problems = [];

// 1. Static: no node builtins in either browser output file.
const NODE_HINTS = [
  'from"node:',
  "from 'node:",
  'require("node:',
  "require('node:",
  'require("fs")',
  'require("os")',
  'require("path")',
  'require("url")',
  'require("zlib")',
];
for (const [label, url] of [
  ["dist/browser/index.js", ESM],
  ["dist/browser/index.cjs", CJS],
]) {
  const text = readFileSync(url, "utf8");
  for (const hint of NODE_HINTS) {
    if (text.includes(hint))
      problems.push(`${label} references a node builtin: ${hint}`);
  }
}

// 2. Functional: import the browser bundle and exercise the fs-free seam.
const {
  isValidId,
  checkId,
  checkIdAsync,
  snapshots,
  setRemoteTransport,
  resetRemoteTransport,
} = await import(ESM);

if (isValidId("MONDO:0005148", "mondo") !== true) {
  problems.push("pattern mode failed on a valid id in the browser bundle");
}
if (isValidId("mondo:5148", "mondo") !== false) {
  problems.push("pattern mode failed on a malformed id in the browser bundle");
}

// No filesystem means no snapshots, and cache mode fails cleanly (not a crash).
if (snapshots().length !== 0) {
  problems.push("snapshots() should be empty in the browser bundle");
}
let cacheThrew = false;
try {
  checkId("MONDO:0005148", "mondo", { how: "cache", version: "sample" });
} catch (e) {
  cacheThrew = true;
  if (e?.code !== "missing_dependency") {
    problems.push(`cache mode threw the wrong error in the browser: ${e?.code}`);
  }
}
if (!cacheThrew) problems.push("cache mode should throw without a filesystem");

// Remote mode works through an injected transport (fetch in a real browser).
setRemoteTransport({
  get: async () => ({ status: 200, body: { entryType: "UniProtKB reviewed" } }),
  post: async () => ({ status: 200, body: null }),
});
try {
  const [row] = await checkIdAsync("P04637", "uniprot", { how: "remote" });
  if (row.valid !== true)
    problems.push("remote mode failed through an injected transport");
} finally {
  resetRemoteTransport();
}

if (problems.length > 0) {
  console.error(`browser check failed:\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
console.log("browser check ok: bundle is filesystem-free and pattern/remote work");
