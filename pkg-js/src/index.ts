// Public entry point for the biobouncer JavaScript/TypeScript package.
//
// The API mirrors the R and Python packages and returns the same verdicts,
// enforced by the shared conformance corpus. Names are idiomatic camelCase in
// memory; serialized output uses the shared snake_case schema so result data is
// identical across languages. This file grows as each phase lands.

// A named import so the bundler pulls in only the version, not all of package.json.
import { version as pkgVersion } from "../package.json";

/** The installed package version. */
export const version: string = pkgVersion;

export type { SnapshotRow } from "./cache";
export { cacheDir, snapshots } from "./cache";
export type { CheckOptions } from "./core";
export { checkId, checkIdAsync, isValidId, isValidIdAsync } from "./core";
export * from "./errors";
export type { SourceInfo, SourceSpec, SpeciesEntry } from "./registry";
export { sourceInfo, sources } from "./registry";
export type { RemoteResponse, RemoteTransport } from "./remote";
export { resetRemoteTransport, setRemoteTransport } from "./remote";
export type { ReportRow, ReportSummary } from "./report";
export { Report, report, reportAsync } from "./report";
export type { Mode, Result, Summary } from "./schema";
export { SCHEMA_VERSION } from "./schema";
export type { SynthOptions, SynthRow } from "./synthesize";
export { synthesize } from "./synthesize";
