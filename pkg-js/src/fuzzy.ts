// Fuzzy "did you mean" for cache mode, ported from pkg-py/src/biobouncer/_fuzzy.py.
// Bounded unit-cost Levenshtein (insert/delete/substitute = 1, no transposition),
// nearest candidate within k, ties broken by the code-point-smallest candidate in
// the snapshot's own spelling.

/** Candidate ids bucketed by length, for length-based pruning. */
export type FuzzyIndex = Map<number, string[]>;

export function fuzzyIndex(ids: Iterable<string>): FuzzyIndex {
  const buckets: FuzzyIndex = new Map();
  for (const c of ids) {
    const arr = buckets.get(c.length);
    if (arr) arr.push(c);
    else buckets.set(c.length, [c]);
  }
  return buckets;
}

/** Edit distance between `a` and `b`, or null when it exceeds `k`. */
export function boundedLevenshtein(a: string, b: string, k: number): number | null {
  const la = a.length;
  const lb = b.length;
  if (Math.abs(la - lb) > k) return null;

  // Typed arrays index as number (not number | undefined), and we reuse both rows.
  let prev = new Int32Array(lb + 1);
  let cur = new Int32Array(lb + 1);
  for (let j = 0; j <= lb; j++) prev[j] = j;

  for (let i = 1; i <= la; i++) {
    cur[0] = i;
    let rowMin = i;
    const ai = a.charCodeAt(i - 1);
    for (let j = 1; j <= lb; j++) {
      // j is in [1, lb] and both rows have length lb + 1, so every read is in
      // bounds; the ?? 0 only satisfies noUncheckedIndexedAccess.
      const up = prev[j] ?? 0;
      const left = cur[j - 1] ?? 0;
      const diag = prev[j - 1] ?? 0;
      const cost = ai === b.charCodeAt(j - 1) ? 0 : 1;
      const v = Math.min(up + 1, left + 1, diag + cost);
      cur[j] = v;
      if (v < rowMin) rowMin = v;
    }
    if (rowMin > k) return null;
    const swap = prev;
    prev = cur;
    cur = swap;
  }

  const d = prev[lb] ?? 0;
  return d <= k ? d : null;
}

/**
 * The nearest candidate to `s` within `maxDistance`, or null. With `ignoreCase`,
 * distance is measured on lowercased forms but the candidate is returned and
 * tie-broken in its original spelling.
 */
export function fuzzySuggest(
  s: string,
  index: FuzzyIndex,
  maxDistance: number,
  ignoreCase = false,
): string | null {
  let best: string | null = null;
  let bestDistance = maxDistance + 1;
  const probe = ignoreCase ? s.toLowerCase() : s;
  const length = s.length;

  for (let candLen = length - maxDistance; candLen <= length + maxDistance; candLen++) {
    const bucket = index.get(candLen);
    if (!bucket) continue;
    for (const cand of bucket) {
      const target = ignoreCase ? cand.toLowerCase() : cand;
      const d = boundedLevenshtein(probe, target, maxDistance);
      if (d === null) continue;
      if (d < bestDistance || (d === bestDistance && (best === null || cand < best))) {
        bestDistance = d;
        best = cand;
      }
    }
  }
  return best;
}
