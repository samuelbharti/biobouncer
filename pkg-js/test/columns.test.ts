// Column fixtures: for every source, feed the synthetic messy column through
// report() and assert the summary tallies, the repair substitution, and the
// per-row isValidId mapping, matching the R and Python column tests.

import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { isValidId } from "../src/core";
import { sourceInfo, sources } from "../src/registry";
import { report } from "../src/report";
import type { Mode } from "../src/schema";
import type { SynthCategory as Category } from "../src/synthesize";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-cols-"));

const here = dirname(fileURLToPath(import.meta.url));
const colDir = join(here, "..", "src", "_data", "fixtures", "columns");

interface ColRow {
  input: string | null;
  category: Category;
  expect: {
    valid: boolean | null;
    normalized: string | null;
    suggestion: string | null;
  };
}

function loadRows(file: string): ColRow[] {
  return readFileSync(file, "utf8")
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l) as ColRow);
}

const cacheKeys = new Set(
  sourceInfo()
    .filter((s) => s.modes.includes("cache"))
    .map((s) => s.key),
);

function checkColumn(
  src: string,
  how: Mode,
  version: string | null,
  rows: ColRow[],
): void {
  const column = rows.map((r) => r.input);
  const count = (c: Category): number => rows.filter((r) => r.category === c).length;

  const rep = report(column, src, { how, version });
  const s = rep.summary;
  expect(s.total).toBe(rows.length);
  expect(s.valid).toBe(count("valid"));
  expect(s.repairable).toBe(count("repairable"));
  expect(s.invalid).toBe(count("invalid") + count("repairable"));
  expect(s.missing).toBe(count("missing"));
  expect(s.indeterminate).toBe(0);

  const expectedRepair = rows.map((r) =>
    r.category === "repairable" ? r.expect.suggestion : r.input,
  );
  expect(rep.repair()).toEqual(expectedRepair);

  const expectedValids = rows.map((r) =>
    r.category === "valid" ? true : r.category === "missing" ? null : false,
  );
  expect(isValidId(column, src, { how, version })).toEqual(expectedValids);
}

describe("column fixtures", () => {
  for (const src of sources()) {
    it(`${src} (pattern)`, () => {
      const file = join(colDir, `${src}.cases.jsonl`);
      expect(existsSync(file), `${src}.cases.jsonl exists`).toBe(true);
      checkColumn(src, "pattern", null, loadRows(file));
    });

    if (cacheKeys.has(src)) {
      it(`${src} (cache)`, () => {
        const file = join(colDir, `${src}.cache.jsonl`);
        expect(existsSync(file), `${src}.cache.jsonl exists`).toBe(true);
        checkColumn(src, "cache", "sample", loadRows(file));
      });
    }
  }
});
