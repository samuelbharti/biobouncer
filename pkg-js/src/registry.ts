// The source registry. Loads the compiled source specs (produced from the
// vendored YAML by scripts/bundle-shared.mjs) and exposes the source list and
// metadata. The spec fields keep the shared snake_case names; the public
// sourceInfo() surface is camelCase.

import { UnknownSourceError } from "./errors";
import sourcesRaw from "./generated/sources.json";
import type { Mode } from "./schema";

/** One entry in a species map (Ensembl prefix scheme or UniProt organism scheme). */
export interface SpeciesEntry {
  name?: string;
  taxon?: number;
  prefix?: string;
}

/** A source definition, mirroring the shared YAML spec (snake_case keys). */
export interface SourceSpec {
  key: string;
  name?: string;
  description?: string;
  pattern: string;
  example?: string | null;
  species_aware?: boolean;
  version_aware?: boolean;
  curie?: { prefix: string; pad_to?: number } | null;
  normalize?: {
    case?: "upper" | "lower";
    rewrite?: Array<{ from: string; to: string }>;
  } | null;
  cache?: Record<string, unknown> | null;
  remote?: Record<string, unknown> | null;
  species?: { scheme: string; map: SpeciesEntry[] } | null;
  default_version?: string | null;
  suggest?: {
    case_insensitive?: boolean;
    fuzzy?: { max_distance: number };
  } | null;
}

/** Public, camelCase metadata for one source. */
export interface SourceInfo {
  key: string;
  name: string;
  example: string | null;
  modes: Mode[];
  speciesAware: boolean;
  versionAware: boolean;
}

const SPECS = sourcesRaw as unknown as SourceSpec[];
const BY_KEY = new Map<string, SourceSpec>(SPECS.map((s) => [s.key, s]));

/** The modes a source supports: always pattern, plus cache and remote when declared. */
export function modesOf(spec: SourceSpec): Mode[] {
  const modes: Mode[] = ["pattern"];
  if (spec.cache) modes.push("cache");
  if (spec.remote) modes.push("remote");
  return modes;
}

/** All source keys, sorted. */
export function sources(): string[] {
  return [...BY_KEY.keys()].sort();
}

/** The spec for `key`, or throw UnknownSourceError. */
export function getSource(key: string): SourceSpec {
  const spec = BY_KEY.get(key);
  if (spec === undefined) {
    throw new UnknownSourceError(`unknown source: ${key}`);
  }
  return spec;
}

/** Metadata for every source, sorted by key. */
export function sourceInfo(): SourceInfo[] {
  return sources().map((key) => {
    const s = getSource(key);
    return {
      key: s.key,
      name: s.name ?? s.key,
      example: s.example ?? null,
      modes: modesOf(s),
      speciesAware: Boolean(s.species_aware),
      versionAware: Boolean(s.version_aware),
    };
  });
}
