// Synthetic parity: synthesize() must reproduce the committed column fixtures
// element for element, the cross-language freshness gate. Also check determinism,
// category coverage, and the unknown-source error.

import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { UnknownSourceError } from "../src/errors";
import { sourceInfo, sources } from "../src/registry";
import { synthesize } from "../src/synthesize";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-synth-"));

const here = dirname(fileURLToPath(import.meta.url));
const colDir = join(here, "..", "src", "_data", "fixtures", "columns");

// Sources whose example admits no wrong-case/unpadded repair.
const NO_REPAIRABLE = new Set(["ec", "hgnc", "hgvs"]);
const cacheKeys = new Set(
  sourceInfo()
    .filter((s) => s.modes.includes("cache"))
    .map((s) => s.key),
);

function loadFixture(file: string): unknown[] {
  return readFileSync(file, "utf8")
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

function asFixtureRows(src: string, how: "pattern" | "cache"): unknown[] {
  const rows = synthesize(
    src,
    how === "cache" ? { how: "cache", version: "sample" } : {},
  );
  return rows.map((r) => {
    const out: Record<string, unknown> = { input: r.input, source_db: src, how };
    if (how === "cache") out.version = "sample";
    out.category = r.category;
    out.expect = { valid: r.valid, normalized: r.normalized, suggestion: r.suggestion };
    return out;
  });
}

describe("synthetic parity", () => {
  for (const src of sources()) {
    it(`${src} reproduces the pattern fixture`, () => {
      const file = join(colDir, `${src}.cases.jsonl`);
      expect(existsSync(file)).toBe(true);
      expect(asFixtureRows(src, "pattern")).toEqual(loadFixture(file));
    });

    if (cacheKeys.has(src)) {
      it(`${src} reproduces the cache fixture`, () => {
        const file = join(colDir, `${src}.cache.jsonl`);
        expect(existsSync(file)).toBe(true);
        expect(asFixtureRows(src, "cache")).toEqual(loadFixture(file));
      });
    }
  }

  it("is deterministic", () => {
    expect(synthesize("mondo")).toEqual(synthesize("mondo"));
  });

  it("covers the categories", () => {
    for (const src of sources()) {
      const cats = new Set(synthesize(src).map((r) => r.category));
      expect(cats.has("valid"), `${src} valid`).toBe(true);
      expect(cats.has("invalid"), `${src} invalid`).toBe(true);
      expect(cats.has("missing"), `${src} missing`).toBe(true);
      if (!NO_REPAIRABLE.has(src)) {
        expect(cats.has("repairable"), `${src} repairable`).toBe(true);
      }
    }
  });

  it("rejects an unknown source", () => {
    expect(() => synthesize("not_a_source")).toThrow(UnknownSourceError);
  });
});
