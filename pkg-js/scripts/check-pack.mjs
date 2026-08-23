// Verify the published tarball carries what the package needs and nothing it
// should not: the compiled entry points and the snapshots must be present, and
// the corpus, fixtures, and sources must never leak. The npm analog of
// tools/check_dist.py.

import { execSync } from "node:child_process";

const out = execSync("npm pack --dry-run --json", { encoding: "utf8" });
const files = JSON.parse(out)[0].files.map((f) => f.path);

const problems = [];
if (!files.includes("dist/index.js")) problems.push("missing dist/index.js (ESM)");
if (!files.includes("dist/index.cjs")) problems.push("missing dist/index.cjs (CJS)");
if (!files.includes("dist/index.d.ts"))
  problems.push("missing dist/index.d.ts (types)");
if (!files.includes("dist/browser/index.js"))
  problems.push("missing dist/browser/index.js (browser ESM)");
if (!files.includes("dist/browser/index.cjs"))
  problems.push("missing dist/browser/index.cjs (browser CJS)");
if (!files.some((f) => f.startsWith("dist/_data/snapshots/"))) {
  problems.push("missing dist/_data/snapshots");
}
for (const leak of ["/corpus/", "/fixtures/", "/generated/"]) {
  if (files.some((f) => f.includes(leak)))
    problems.push(`leaked ${leak} into the tarball`);
}
if (files.some((f) => f.startsWith("src/")))
  problems.push("leaked src/ into the tarball");

if (problems.length > 0) {
  console.error(`pack check failed:\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
console.log(`pack check ok: ${files.length} files`);
