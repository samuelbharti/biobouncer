// Compile the vendored source specs into a single JSON the runtime imports, so
// the published package needs no YAML parser at runtime. Reads the vendored
// src/_data/sources/*.yaml (mirrored from shared/ by tools/sync_shared.py) and
// writes src/generated/sources.json. Run by the prebuild and pretest scripts.

import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const srcDir = join(root, "src", "_data", "sources");
const outDir = join(root, "src", "generated");
const outFile = join(outDir, "sources.json");

const files = readdirSync(srcDir)
  .filter((f) => f.endsWith(".yaml"))
  .sort();
const sources = files.map((f) => parse(readFileSync(join(srcDir, f), "utf8")));

mkdirSync(outDir, { recursive: true });
writeFileSync(outFile, `${JSON.stringify(sources, null, 2)}\n`);
console.log(`bundled ${sources.length} sources -> ${outFile}`);
