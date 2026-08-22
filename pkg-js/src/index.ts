// Public entry point for the biobouncer JavaScript/TypeScript package.
//
// The API mirrors the R and Python packages and returns the same verdicts,
// enforced by the shared conformance corpus. Names are idiomatic camelCase in
// memory; serialized output uses the shared snake_case schema so result data is
// identical across languages. This file grows as each phase lands.

import pkg from "../package.json";

/** The installed package version. */
export const version: string = pkg.version;

/** The result-schema version shared across the R, Python, and JS packages. */
export const SCHEMA_VERSION = "2" as const;
