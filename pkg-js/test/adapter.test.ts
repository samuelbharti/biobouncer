import { describe, expect, it } from "vitest";
import { idSchema } from "../src/adapters/standard-schema";

function validate(schema: ReturnType<typeof idSchema>, value: unknown) {
  return schema["~standard"].validate(value);
}

describe("standard schema adapter", () => {
  const schema = idSchema("mondo");

  it("accepts a valid id", async () => {
    const r = await validate(schema, "MONDO:0005148");
    expect(r).toEqual({ value: "MONDO:0005148" });
  });

  it("rejects an invalid id and suggests a repair", async () => {
    const r = await validate(schema, "mondo:5148");
    if (!("issues" in r) || r.issues === undefined) throw new Error("expected issues");
    expect(r.issues[0]?.message).toContain("MONDO:0005148");
  });

  it("passes a missing value (null or undefined)", async () => {
    expect(await validate(schema, null)).toEqual({ value: null });
    expect(await validate(schema, undefined)).toEqual({ value: undefined });
  });

  it("rejects a non-string value", async () => {
    const r = await validate(schema, 42);
    expect("issues" in r).toBe(true);
  });

  it("exposes the Standard Schema shape", () => {
    expect(schema["~standard"].version).toBe(1);
    expect(schema["~standard"].vendor).toBe("biobouncer");
  });
});
