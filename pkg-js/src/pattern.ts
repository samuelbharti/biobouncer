// Pattern mode: offline, deterministic checks against a source regex, ported
// from pkg-py/src/biobouncer/_pattern.py. The regexes use ASCII classes so R
// (PCRE), Python (re), and JavaScript (RegExp) agree element for element.

import type { SourceSpec } from "./registry";

const compiled = new Map<string, RegExp>();

/** Whether `s` matches `pattern` in full. */
export function matches(pattern: string, s: string): boolean {
  let re = compiled.get(pattern);
  if (re === undefined) {
    // Wrap in a non-capturing group so the anchors bind to the whole pattern,
    // not just one branch of a top-level alternation. No flags: JS `$` without
    // `m` matches only true end-of-input, equal to Python's re.fullmatch.
    re = new RegExp(`^(?:${pattern})$`);
    compiled.set(pattern, re);
  }
  return re.test(s);
}

const DIGITS = /^[0-9]+$/;

/** Split on the first occurrence of `sep`: [head, found, tail]. */
export function partitionFirst(s: string, sep: string): [string, boolean, string] {
  const i = s.indexOf(sep);
  if (i < 0) return [s, false, ""];
  return [s.slice(0, i), true, s.slice(i + sep.length)];
}

/** A repair for `s`, or null: a wrong-case or unpadded form that maps to a valid id. */
export function suggest(spec: SourceSpec, s: string): string | null {
  const curie = spec.curie;
  if (curie) {
    const prefix = curie.prefix;
    const padTo = curie.pad_to;
    let [head, sep, local] = partitionFirst(s, ":");
    if (!sep) {
      head = prefix;
      local = s;
    }
    if (head.toUpperCase() !== prefix.toUpperCase()) return null;
    if (padTo && DIGITS.test(local)) {
      local = local.padStart(padTo, "0");
    }
    const candidate = `${prefix}:${local}`;
    if (candidate !== s && matches(spec.pattern, candidate)) return candidate;
    return null;
  }

  const norm = spec.normalize;
  if (norm && (norm.case === "upper" || norm.case === "lower")) {
    const candidate = norm.case === "upper" ? s.toUpperCase() : s.toLowerCase();
    if (candidate !== s && matches(spec.pattern, candidate)) return candidate;
  }
  return null;
}

// ENS, a greedy species code, one feature letter, then 11 digits. The greedy
// [A-Z]* plus the single [EFGPT] yields "" for ENSG... and "MUS" for ENSMUSG...
const ENSEMBL_ID = /^ENS([A-Z]*)[EFGPT][0-9]{11}$/;

function ensemblIdPrefix(ident: string): string | null {
  const m = ENSEMBL_ID.exec(ident);
  if (m === null) return null;
  return m[1] ?? "";
}

function ensemblSpeciesPrefix(
  block: NonNullable<SourceSpec["species"]>,
  species: string | number,
): string | null {
  for (const entry of block.map) {
    // Name match stringifies both sides; taxon match fires only for a numeric
    // species, so 9606 matches taxon 9606 but "9606" does not.
    if (
      String(entry.name) === String(species) ||
      (typeof species === "number" && entry.taxon === species)
    ) {
      return entry.prefix ?? null;
    }
  }
  return null;
}

function speciesOk(
  spec: SourceSpec,
  ident: string,
  species: string | number | null,
): boolean {
  if (species === null) return true;
  const block = spec.species;
  if (!block) return true;
  if (block.scheme !== "ensembl_prefix") return true;
  const expected = ensemblSpeciesPrefix(block, species);
  if (expected === null) return true;
  const idPrefix = ensemblIdPrefix(ident);
  if (idPrefix === null) return true;
  return idPrefix === expected;
}

export interface PatternVerdict {
  valid: boolean;
  normalized: string | null;
  suggestion: string | null;
}

/** Return the pattern-mode verdict for a single input. */
export function checkOne(
  spec: SourceSpec,
  s: string,
  species: string | number | null = null,
): PatternVerdict {
  if (matches(spec.pattern, s)) {
    if (speciesOk(spec, s, species)) {
      return { valid: true, normalized: s, suggestion: null };
    }
    return { valid: false, normalized: null, suggestion: null };
  }
  const candidate = suggest(spec, s);
  if (candidate !== null && speciesOk(spec, candidate, species)) {
    return { valid: false, normalized: null, suggestion: candidate };
  }
  return { valid: false, normalized: null, suggestion: null };
}
