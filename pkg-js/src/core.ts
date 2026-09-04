// Dispatch: checkId (sync, offline) and checkIdAsync (all modes). Ported from
// pkg-py/src/biobouncer/core.py. Network I/O is async in JS, so remote mode is
// only available through the async entry points.

import {
  buildFuzzy,
  cacheCheck,
  defaultCacheVersion,
  type FuzzyConfig,
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
import { getSource, type SourceSpec } from "./registry";
import { remoteVerdicts, utcStamp } from "./remote";
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

type OnError = "raise" | "indeterminate";

interface Prepared {
  how: Mode;
  onError: OnError;
  species: string | number | null;
  spec: SourceSpec;
}

type OfflinePlan =
  | { mode: "pattern" }
  | {
      mode: "cache";
      ids: Set<string>;
      retired: Map<string, string>;
      fuzzy: FuzzyConfig | null;
      version: string;
    };

type Plan = OfflinePlan | { mode: "remote"; version: string };

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

function prepare(sourceDb: string, opts: CheckOptions): Prepared {
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
  return { how, onError, species: opts.species ?? null, spec: getSource(sourceDb) };
}

function planDispatch(
  how: Mode,
  sourceDb: string,
  spec: SourceSpec,
  opts: CheckOptions,
): Plan {
  if (how === "pattern") return { mode: "pattern" };

  if (how === "cache") {
    const version =
      opts.version != null ? String(opts.version) : defaultCacheVersion(sourceDb, spec);
    if (version === null) {
      throw new MissingVersionError(`no snapshot version available for ${sourceDb}`);
    }
    const ids = snapshotSet(sourceDb, version);
    return {
      mode: "cache",
      ids,
      retired: snapshotRetired(sourceDb, version),
      fuzzy: buildFuzzy(spec, ids),
      version,
    };
  }

  if (how === "existence") {
    // Same as R and Python: a snapshot answers only when the caller names a
    // version. With no version the check goes live, or degrades to pattern.
    if (opts.version != null) {
      const version = String(opts.version);
      if (hasSnapshot(sourceDb, version)) {
        const ids = snapshotSet(sourceDb, version);
        return {
          mode: "cache",
          ids,
          retired: snapshotRetired(sourceDb, version),
          fuzzy: buildFuzzy(spec, ids),
          version,
        };
      }
    }
    if (spec.remote) return { mode: "remote", version: utcStamp() };
    return { mode: "pattern" };
  }

  return { mode: "remote", version: utcStamp() };
}

function assembleOffline(
  items: Array<string | null>,
  plan: OfflinePlan,
  spec: SourceSpec,
  species: string | number | null,
  how: Mode,
  sourceDb: string,
): Result[] {
  const version = plan.mode === "cache" ? plan.version : null;
  return items.map((s): Result => {
    let valid: boolean | null = null;
    let normalized: string | null = null;
    let suggestion: string | null = null;
    if (s !== null) {
      const v =
        plan.mode === "cache"
          ? cacheCheck(spec, s, plan.ids, plan.retired, plan.fuzzy)
          : checkOne(spec, s, species);
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
      version,
      species,
      how,
      error: null,
    };
  });
}

/** Validate a scalar or batch offline (pattern, cache, or existence-with-snapshot). */
export function checkId(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: CheckOptions = {},
): Result[] {
  const { how, species, spec } = prepare(sourceDb, opts);
  const plan = planDispatch(how, sourceDb, spec, opts);
  if (plan.mode === "remote") {
    throw new BiobouncerError(
      `${how} mode needs the network; use checkIdAsync`,
      "needs_async",
    );
  }
  return assembleOffline(toItems(x), plan, spec, species, how, sourceDb);
}

/** Validate a scalar or batch in any mode, including remote. */
export async function checkIdAsync(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: CheckOptions = {},
): Promise<Result[]> {
  const { how, onError, species, spec } = prepare(sourceDb, opts);
  const plan = planDispatch(how, sourceDb, spec, opts);
  const items = toItems(x);
  if (plan.mode !== "remote") {
    return assembleOffline(items, plan, spec, species, how, sourceDb);
  }

  const verdicts = await remoteVerdicts(
    spec,
    items,
    species,
    onError,
    opts.refresh ?? false,
  );
  const out: Result[] = [];
  for (let i = 0; i < items.length; i++) {
    const v = verdicts[i];
    if (v === undefined) throw new Error("verdict length mismatch");
    out.push({
      input: items[i] ?? null,
      valid: v.valid,
      normalized: v.normalized,
      suggestion: v.suggestion,
      sourceDb,
      version: v.fetchedAt ?? plan.version,
      species,
      how,
      error: v.error,
    });
  }
  return out;
}

function scalarize(
  x: unknown,
  results: Result[],
): boolean | null | Array<boolean | null> {
  if (isScalarInput(x)) {
    const first = results[0];
    return first ? first.valid : null;
  }
  return results.map((r) => r.valid);
}

/** Convenience over checkId: a bare verdict for a scalar, a list for a batch. */
export function isValidId(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: Omit<CheckOptions, "onError"> = {},
): boolean | null | Array<boolean | null> {
  return scalarize(x, checkId(x, sourceDb, opts));
}

/** Async isValidId supporting every mode, including remote. */
export async function isValidIdAsync(
  x: string | Iterable<string | null | undefined>,
  sourceDb: string,
  opts: Omit<CheckOptions, "onError"> = {},
): Promise<boolean | null | Array<boolean | null>> {
  return scalarize(x, await checkIdAsync(x, sourceDb, opts));
}
