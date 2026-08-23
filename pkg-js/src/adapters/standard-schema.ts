// A Standard Schema (https://standardschema.dev) adapter, so a biobouncer id
// check plugs into Zod, Valibot, ArkType, and anything else that speaks the spec.
// It delegates to checkIdAsync (async, so every mode including remote works) and
// follows the missing-passes rule: a null or undefined value is not a failure.

import { checkIdAsync } from "../core";
import type { Mode } from "../schema";

/** The subset of the Standard Schema v1 interface this adapter implements. */
export interface StandardSchemaV1<Input = string, Output = Input> {
  readonly "~standard": {
    readonly version: 1;
    readonly vendor: string;
    readonly validate: (
      value: unknown,
    ) => StandardResult<Output> | Promise<StandardResult<Output>>;
    readonly types?: { readonly input: Input; readonly output: Output };
  };
}

type StandardResult<T> =
  | { readonly value: T; readonly issues?: undefined }
  | { readonly issues: ReadonlyArray<{ readonly message: string }> };

export interface IdSchemaOptions {
  how?: Mode;
  species?: string | number | null;
  version?: string | null;
}

/**
 * A Standard Schema that accepts a valid identifier for `sourceDb`. A null or
 * undefined value passes (missing is not a failure); any other non-string fails;
 * an invalid id fails with a message that includes the suggestion when there is
 * one.
 */
export function idSchema(
  sourceDb: string,
  opts: IdSchemaOptions = {},
): StandardSchemaV1<string> {
  return {
    "~standard": {
      version: 1,
      vendor: "biobouncer",
      async validate(value: unknown): Promise<StandardResult<string>> {
        if (value === null || value === undefined) {
          // Missing is not a failure; pass the value through unchanged.
          return { value: value as unknown as string };
        }
        if (typeof value !== "string") {
          return { issues: [{ message: "expected a string identifier" }] };
        }
        const result = (await checkIdAsync(value, sourceDb, opts))[0];
        if (!result || result.valid === true || result.valid === null) {
          return { value };
        }
        const hint = result.suggestion ? ` (did you mean ${result.suggestion}?)` : "";
        return { issues: [{ message: `not a valid ${sourceDb} identifier${hint}` }] };
      },
    },
  };
}
