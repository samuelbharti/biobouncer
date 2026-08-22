// Run the shared cross-language conformance corpus against the JS package. This
// is the parity contract: R, Python, and JS must produce the same valid,
// normalized, and suggestion for every case. Pattern-mode cases run here; cache
// and remote cases join as those modes land.

import { mkdtempSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { checkId } from "../src/core";
import type { Mode, Result } from "../src/schema";

// Point the cache at an empty temp dir so cache cases resolve to the bundled
// sample snapshots, matching the Python and R conformance suites.
process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-conf-"));

const here = dirname(fileURLToPath(import.meta.url));
const corpusDir = join(here, "..", "src", "_data", "corpus");

interface Case {
  input: string;
  source_db: string;
  how: string;
  species?: string | number | null;
  version?: string | null;
  expect: { valid?: boolean | null; normalized?: string; suggestion?: string };
  note?: string;
}

function loadCases(): Case[] {
  const cases: Case[] = [];
  for (const f of readdirSync(corpusDir)
    .filter((n) => n.endsWith(".jsonl"))
    .sort()) {
    for (const line of readFileSync(join(corpusDir, f), "utf8").split(/\r?\n/)) {
      const t = line.trim();
      if (t) cases.push(JSON.parse(t) as Case);
    }
  }
  return cases;
}

function only(results: Result[]): Result {
  const r = results[0];
  if (r === undefined) throw new Error("expected exactly one result");
  return r;
}

const CASES = loadCases();
const OFFLINE_CASES = CASES.filter((c) => c.how === "pattern" || c.how === "cache");

describe("conformance (offline)", () => {
  it("the corpus is not empty", () => {
    expect(OFFLINE_CASES.length).toBeGreaterThan(0);
  });

  it.each(OFFLINE_CASES)("$source_db $how $input", (c) => {
    const r = only(
      checkId(c.input, c.source_db, {
        how: c.how as Mode,
        species: c.species ?? null,
        version: c.version ?? null,
      }),
    );
    expect(r.valid).toBe(c.expect.valid ?? null);
    expect(r.normalized).toBe(c.expect.normalized ?? null);
    expect(r.suggestion).toBe(c.expect.suggestion ?? null);
  });
});
