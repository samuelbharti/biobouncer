// Validate and report on a whole column, ported from pkg-py/src/biobouncer/report.py.
// report() classifies the column; Report.repair() substitutes the fixable values.

import { type CheckOptions, checkId } from "./core";
import { type Result, type Summary, summarize } from "./schema";

export type ReportSummary = Summary;

/** A per-row view of a result: the varying columns, without the report-level constants. */
export interface ReportRow {
  input: string | null;
  valid: boolean | null;
  normalized: string | null;
  suggestion: string | null;
  error: string | null;
}

export class Report {
  readonly results: Result[];
  readonly sourceDb: string;
  readonly how: string;

  constructor(results: Result[], sourceDb: string, how: string) {
    this.results = results;
    this.sourceDb = sourceDb;
    this.how = how;
  }

  get length(): number {
    return this.results.length;
  }

  get summary(): ReportSummary {
    return summarize(this.results);
  }

  /** The per-row table (input, valid, normalized, suggestion, error). */
  toRows(): ReportRow[] {
    return this.results.map((r) => ({
      input: r.input,
      valid: r.valid,
      normalized: r.normalized,
      suggestion: r.suggestion,
      error: r.error,
    }));
  }

  /** The column with every fixable cell replaced by its suggestion. */
  repair(): Array<string | null> {
    return this.results.map((r) =>
      r.valid === false && r.suggestion !== null ? r.suggestion : r.input,
    );
  }

  toString(): string {
    const s = this.summary;
    const unmappable = s.invalid - s.repairable;
    let parts = `${s.valid} valid, ${s.repairable} repairable, ${unmappable} invalid, ${s.missing} missing`;
    if (s.indeterminate > 0) parts += `, ${s.indeterminate} indeterminate`;
    return `<biobouncer report on '${this.sourceDb}' (${this.how} mode): ${parts} of ${s.total}>`;
  }
}

/** Validate a column and return a Report. */
export function report(
  column: Iterable<string | null | undefined>,
  sourceDb: string,
  opts: CheckOptions = {},
): Report {
  const results = checkId(column, sourceDb, opts);
  return new Report(results, sourceDb, opts.how ?? "pattern");
}
