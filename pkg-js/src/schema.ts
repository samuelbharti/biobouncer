// Result and mode types, shared across every checking mode.
//
// In memory the Result uses idiomatic camelCase field names. Serialization
// (the CLI and any toJSON) emits the snake_case names in RESULT_FIELDS so the
// wire format is identical to the R and Python packages and to
// shared/schema/result.json.

/** A checking mode passed as `how`. */
export type Mode = "pattern" | "cache" | "remote" | "existence";

/** The result-schema version shared across the R, Python, and JS packages. */
export const SCHEMA_VERSION = "2" as const;

/** Serialized result field names, in schema order (the snake_case wire form). */
export const RESULT_FIELDS = [
  "input",
  "valid",
  "normalized",
  "suggestion",
  "source_db",
  "version",
  "species",
  "how",
  "error",
] as const;

/** Serialized summary field names, in schema order. */
export const SUMMARY_FIELDS = [
  "total",
  "valid",
  "invalid",
  "repairable",
  "missing",
  "indeterminate",
] as const;

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
