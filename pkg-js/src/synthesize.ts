// Build a synthetic, labeled column of ids for any source, ported from
// pkg-py/src/biobouncer/synthetic.py. Every value is labeled by running the
// checker itself, so the labels are correct and match synthesize_ids in R.

import { snapshotRetired, snapshotSet } from "./cache";
import { checkId } from "./core";
import { partitionFirst } from "./pattern";
import { getSource, type SourceSpec } from "./registry";
import type { Mode, Result } from "./schema";

export interface SynthRow {
  input: string | null;
  /** How the checker classifies the value. */
  category: "valid" | "repairable" | "invalid" | "missing";
  valid: boolean | null;
  normalized: string | null;
  suggestion: string | null;
}

type Category = SynthRow["category"];

const CATEGORIES: Category[] = ["valid", "repairable", "invalid", "missing"];
const BREAKERS = ["!", " x", "##"];
const ABSENT_OFFSET = 9_000_000;

export interface SynthOptions {
  how?: Mode;
  version?: string | null;
  nValid?: number;
  nRepairable?: number;
  nInvalid?: number;
  missing?: number;
  seed?: number;
}

const DIGIT_RUN = /[0-9]+/g;

/** Return `s` with its last run of digits increased by `delta`, keeping its width. */
function incrementLastDigitRun(s: string, delta: number): string | null {
  const runs = [...s.matchAll(DIGIT_RUN)];
  const run = runs[runs.length - 1];
  if (run === undefined || run.index === undefined) return null;
  const digits = run[0];
  const value = Number.parseInt(digits, 10) + delta;
  if (value < 0) return null;
  const replacement = String(value).padStart(digits.length, "0");
  return s.slice(0, run.index) + replacement + s.slice(run.index + digits.length);
}

function validValues(spec: SourceSpec, n: number, seed: number): string[] {
  const example = spec.example;
  if (!example) return [];
  const values = [example];
  for (let i = 1; i < n; i++) {
    const cand = incrementLastDigitRun(example, i + seed);
    if (cand !== null && !values.includes(cand)) values.push(cand);
  }
  return values;
}

function repairableValues(spec: SourceSpec): string[] {
  const example = spec.example;
  if (!example) return [];
  const candidates: string[] = [];
  if (spec.curie) {
    const [head, sep, local] = partitionFirst(example, ":");
    if (sep && head.toLowerCase() !== head) {
      candidates.push(`${head.toLowerCase()}:${local}`);
    }
    if (spec.curie.pad_to && /^[0-9]+$/.test(local)) {
      const stripped = local.replace(/^0+/, "") || "0";
      if (stripped !== local) candidates.push(`${head}:${stripped}`);
    }
    return candidates;
  }
  const c = spec.normalize?.case;
  if (c === "upper" && example.toLowerCase() !== example) {
    candidates.push(example.toLowerCase());
  } else if (c === "lower" && example.toUpperCase() !== example) {
    candidates.push(example.toUpperCase());
  }
  return candidates;
}

function invalidValues(spec: SourceSpec, n: number): string[] {
  const example = spec.example;
  if (!example) return [];
  return BREAKERS.slice(0, n).map((b) => `${example}${b}`);
}

function wellformedAbsent(spec: SourceSpec): string | null {
  const example = spec.example;
  if (!example) return null;
  return incrementLastDigitRun(example, ABSENT_OFFSET);
}

function categorize(r: Result): Category {
  if (r.valid === true) return "valid";
  if (r.valid === null) return "missing";
  if (r.suggestion !== null) return "repairable";
  return "invalid";
}

function labelRow(
  sourceDb: string,
  value: string | null,
  how: Mode,
  version: string | null,
): SynthRow {
  const results = checkId([value], sourceDb, { how, version });
  const r = results[0];
  if (r === undefined) throw new Error("expected one result");
  return {
    input: r.input,
    category: categorize(r),
    valid: r.valid,
    normalized: r.normalized,
    suggestion: r.suggestion,
  };
}

function rowsFor(
  sourceDb: string,
  values: Array<string | null>,
  target: Category,
  limit: number,
  how: Mode,
  version: string | null,
): SynthRow[] {
  const rows: SynthRow[] = [];
  const seen = new Set<string | null>();
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    const r = labelRow(sourceDb, value, how, version);
    if (r.category === target) rows.push(r);
    if (rows.length >= limit) break;
  }
  return rows;
}

function interleave(buckets: Record<Category, SynthRow[]>): SynthRow[] {
  const ordered = CATEGORIES.map((c) => buckets[c]);
  const depth = Math.max(0, ...ordered.map((b) => b.length));
  const out: SynthRow[] = [];
  for (let i = 0; i < depth; i++) {
    for (const bucket of ordered) {
      const item = bucket[i];
      if (item !== undefined) out.push(item);
    }
  }
  return out;
}

/** Build a synthetic, labeled column of ids for one source. */
export function synthesize(sourceDb: string, opts: SynthOptions = {}): SynthRow[] {
  const how = opts.how ?? "pattern";
  const nValid = opts.nValid ?? 2;
  const nRepairable = opts.nRepairable ?? 1;
  const nInvalid = opts.nInvalid ?? 1;
  const missing = opts.missing ?? 1;
  const seed = opts.seed ?? 0;
  const spec = getSource(sourceDb);

  let validVals: Array<string | null>;
  let repairableVals: Array<string | null>;
  let invalidVals: Array<string | null>;
  let version: string | null = null;

  if (how === "cache") {
    version = opts.version ?? "sample";
    const ids = [...snapshotSet(sourceDb, version)].sort();
    const retired = [...snapshotRetired(sourceDb, version).keys()].sort();
    validVals = ids.slice(0, nValid);
    repairableVals = [...retired, ...repairableValues(spec)];
    const absent = wellformedAbsent(spec);
    invalidVals = absent !== null ? [absent] : [];
  } else {
    validVals = validValues(spec, nValid, seed);
    repairableVals = repairableValues(spec);
    invalidVals = invalidValues(spec, BREAKERS.length);
  }

  const buckets: Record<Category, SynthRow[]> = {
    valid: rowsFor(sourceDb, validVals, "valid", nValid, how, version),
    repairable: rowsFor(
      sourceDb,
      repairableVals,
      "repairable",
      nRepairable,
      how,
      version,
    ),
    invalid: rowsFor(sourceDb, invalidVals, "invalid", nInvalid, how, version),
    missing: rowsFor(
      sourceDb,
      Array(missing).fill(null),
      "missing",
      missing,
      how,
      version,
    ),
  };
  return interleave(buckets);
}
