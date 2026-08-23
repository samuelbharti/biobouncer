// Copy the runtime data the published package needs into dist. Only snapshots
// are shipped (cache mode reads them at runtime); the sources are already inlined
// into the bundle, and the corpus and fixtures are test-only.

import { cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const from = join(root, "src", "_data", "snapshots");
const to = join(root, "dist", "_data", "snapshots");

if (!existsSync(from)) {
  console.error(`snapshots not found at ${from}; run sync_shared.py first`);
  process.exit(1);
}
cpSync(from, to, { recursive: true });
console.log(`copied snapshots -> ${to}`);
