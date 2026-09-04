// Existence mode picks its path the way R and Python do: a snapshot only when
// the caller names a version, else live, else a pattern check.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { checkId } from "../src/core";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-exist-"));

describe("existence mode", () => {
  it("answers from a snapshot when a version is named", () => {
    const r = checkId("MONDO:0005148", "mondo", {
      how: "existence",
      version: "sample",
    })[0];
    expect(r?.valid).toBe(true);
    expect(r?.version).toBe("sample");
    expect(r?.how).toBe("existence");
  });

  it("goes live when no version is named and the source has a resolver", () => {
    expect(() => checkId("MONDO:0005148", "mondo", { how: "existence" })).toThrow(
      /needs the network/,
    );
  });

  it("degrades to a pattern check when the source has no resolver", () => {
    const r = checkId("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "inchikey", {
      how: "existence",
    })[0];
    expect(r?.valid).toBe(true);
    expect(r?.version).toBeNull();
    expect(r?.how).toBe("existence");
  });
});
