import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { idSchema } from "../src/adapters/standard-schema";
import { RemoteError } from "../src/errors";
import { resetRemoteTransport, setRemoteTransport } from "../src/remote";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-adapter-"));

afterAll(() => resetRemoteTransport());

function validate(schema: ReturnType<typeof idSchema>, value: unknown) {
  return schema["~standard"].validate(value);
}

describe("standard schema adapter", () => {
  const schema = idSchema("mondo");

  it("rejects an indeterminate verdict instead of passing it", async () => {
    setRemoteTransport({
      get: async () => {
        throw new RemoteError("network down");
      },
      post: async () => {
        throw new RemoteError("network down");
      },
    });
    const live = idSchema("mondo", { how: "remote", onError: "indeterminate" });
    const r = await validate(live, "MONDO:0005148");
    if (!("issues" in r) || r.issues === undefined) throw new Error("expected issues");
    expect(r.issues[0]?.message).toContain("network down");
    resetRemoteTransport();
  });

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
