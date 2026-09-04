// Result and mode types, shared across every checking mode.
//
// In memory the Result uses idiomatic camelCase field names. Serialized output
// uses the snake_case names in RESULT_FIELDS so the wire format is identical to
// the R and Python packages. The version and field lists come from the vendored
// shared/schema/result.json, as they do in R and Python.

import schema from "./_data/schema/result.json";

/** A checking mode passed as `how`. */
export type Mode = "pattern" | "cache" | "remote" | "existence";

/** The result-schema version shared across the R, Python, and JS packages. */
export const SCHEMA_VERSION: string = schema.schema_version;

/** Serialized result field names, in schema order (the snake_case wire form). */
export const RESULT_FIELDS: readonly string[] = schema.result_fields;

/** Serialized summary field names, in schema order. */
export const SUMMARY_FIELDS: readonly string[] = schema.summary_fields;

/** One verdict for one input. camelCase in memory; see RESULT_FIELDS for the wire form. */
export interface Result {
  input: string | null;
  valid: boolean | null;
  normalized: string | null;
  suggestion: string | null;
  sourceDb: string;
  version: string | null;
  species: string | number | null;
  how: Mode;
  error: string | null;
}

/** Counts over a set of results. invalid includes repairables; repairable is a subset. */
export interface Summary {
  total: number;
  valid: number;
  invalid: number;
  repairable: number;
  missing: number;
  indeterminate: number;
}

/** Summarize results with the same semantics as the R and Python packages. */
export function summarize(results: Result[]): Summary {
  let valid = 0;
  let invalid = 0;
  let repairable = 0;
  let missing = 0;
  let indeterminate = 0;
  for (const r of results) {
    if (r.valid === true) {
      valid++;
    } else if (r.valid === false) {
      invalid++;
      if (r.suggestion !== null) repairable++;
    } else if (r.error !== null) {
      indeterminate++;
    } else {
      missing++;
    }
  }
  return { total: results.length, valid, invalid, repairable, missing, indeterminate };
}
