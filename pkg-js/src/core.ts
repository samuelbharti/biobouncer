// Dispatch: checkId and isValidId. Ported from pkg-py/src/biobouncer/core.py.
// Pattern, cache, and existence (offline) modes are wired here; remote lands in a
// later phase.

import {
  buildFuzzy,
  cacheCheck,
  defaultCacheVersion,
  hasSnapshot,
  snapshotRetired,
  snapshotSet,
} from "./cache";
import {
  BiobouncerError,
  InvalidModeError,
  InvalidOnError,
  MissingVersionError,
} from "./errors";
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

const NOT_IMPLEMENTED = "remote mode is not yet implemented in pkg-js";

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

  if (how === "remote") {
    throw new BiobouncerError(NOT_IMPLEMENTED, "not_implemented");
  }

  // Resolve a snapshot for cache, or for existence when one is available.
  let ids: Set<string> | null = null;
  let retired = new Map<string, string>();
  let resultVersion: string | null = null;

  if (how === "cache") {
    const version =
      opts.version != null ? String(opts.version) : defaultCacheVersion(sourceDb, spec);
    if (version === null) {
      throw new MissingVersionError(`no snapshot version available for ${sourceDb}`);
    }
    ids = snapshotSet(sourceDb, version);
    retired = snapshotRetired(sourceDb, version);
    resultVersion = version;
  } else if (how === "existence") {
    const version =
      opts.version != null ? String(opts.version) : defaultCacheVersion(sourceDb, spec);
    if (version !== null && hasSnapshot(sourceDb, version)) {
      ids = snapshotSet(sourceDb, version);
      retired = snapshotRetired(sourceDb, version);
      resultVersion = version;
    } else if (spec.remote) {
      throw new BiobouncerError(NOT_IMPLEMENTED, "not_implemented");
    }
    // else: no snapshot and no resolver, so degrade to pattern (ids stays null).
  }

  const fuzzy = ids !== null ? buildFuzzy(spec, ids) : null;

  return toItems(x).map((s): Result => {
    let valid: boolean | null = null;
    let normalized: string | null = null;
    let suggestion: string | null = null;

    if (s === null) {
      // missing input: null verdict, echoed below.
    } else if (ids !== null) {
      const v = cacheCheck(spec, s, ids, retired, fuzzy);
      valid = v.valid;
      normalized = v.normalized;
      suggestion = v.suggestion;
    } else {
      const v = checkOne(spec, s, species);
      valid = v.valid;
      normalized = v.normalized;
      suggestion = v.suggestion;
    }

    return {
      input: s,
      valid,
      normalized,
      suggestion,
      sourceDb,
      version: resultVersion,
      species,
      how,
      error: null,
    };
  });
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
