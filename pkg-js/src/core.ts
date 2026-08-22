// Dispatch: checkId and isValidId. Ported from pkg-py/src/biobouncer/core.py.
// Pattern mode is wired here; cache, remote, and existence land in later phases.

import { BiobouncerError, InvalidModeError, InvalidOnError } from "./errors";
import { checkOne } from "./pattern";
import { getSource } from "./registry";
import type { Mode, Result } from "./schema";

const KNOWN_MODES = new Set<string>(["pattern", "cache", "remote", "existence"]);
const ON_ERROR = new Set<string>(["raise", "indeterminate"]);

export interface CheckOptions {
  how?: Mode;
  species?: string | number | null;
  version?: string | null;
  refresh?: boolean;
  onError?: "raise" | "indeterminate";
}

function isMissing(v: unknown): boolean {
  return v === null || v === undefined || (typeof v === "number" && Number.isNaN(v));
}

function isIterable(x: unknown): x is Iterable<unknown> {
  return (
    x !== null &&
    x !== undefined &&
    typeof (x as { [Symbol.iterator]?: unknown })[Symbol.iterator] === "function"
  );
}

/** A string is scalar; a non-iterable is scalar; everything else is a batch. */
function isScalarInput(x: unknown): boolean {
  return typeof x === "string" || !isIterable(x);
}

function toItems(x: unknown): Array<string | null> {
  if (typeof x === "string") return [x];
  if (isIterable(x)) {
    const out: Array<string | null> = [];
    for (const it of x) out.push(isMissing(it) ? null : String(it));
    return out;
  }
  return [isMissing(x) ? null : String(x)];
}

/** Validate a scalar or batch of inputs against a source, returning one Result each. */
export function checkId(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: CheckOptions = {},
): Result[] {
  if (typeof sourceDb !== "string") {
    throw new TypeError("sourceDb must be a string");
  }
  const how = opts.how ?? "pattern";
  if (typeof how !== "string" || !KNOWN_MODES.has(how)) {
    throw new InvalidModeError(`unknown mode: ${String(how)}`);
  }
  const onError = opts.onError ?? "raise";
  if (!ON_ERROR.has(onError)) {
    throw new InvalidOnError(`invalid onError: ${onError}`);
  }

  const species = opts.species ?? null;
  const spec = getSource(sourceDb);

  if (how !== "pattern") {
    throw new BiobouncerError(
      `${how} mode is not yet implemented in pkg-js`,
      "not_implemented",
    );
  }

  return toItems(x).map((s): Result => {
    if (s === null) {
      return blankResult(null, sourceDb, species, how);
    }
    const v = checkOne(spec, s, species);
    return {
      input: s,
      valid: v.valid,
      normalized: v.normalized,
      suggestion: v.suggestion,
      sourceDb,
      version: null,
      species,
      how,
      error: null,
    };
  });
}

function blankResult(
  input: string | null,
  sourceDb: string,
  species: string | number | null,
  how: Mode,
): Result {
  return {
    input,
    valid: null,
    normalized: null,
    suggestion: null,
    sourceDb,
    version: null,
    species,
    how,
    error: null,
  };
}

/** Convenience over checkId: a bare verdict for a scalar, a list for a batch. */
export function isValidId(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: Omit<CheckOptions, "onError"> = {},
): boolean | null | Array<boolean | null> {
  const results = checkId(x, sourceDb, opts);
  if (isScalarInput(x)) {
    const first = results[0];
    return first ? first.valid : null;
  }
  return results.map((r) => r.valid);
}
