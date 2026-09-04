import { describe, expect, it } from "vitest";
import { sourceInfo, sources } from "../src/registry";

describe("registry", () => {
  it("lists sources sorted and includes mondo", () => {
    const s = sources();
    expect(s).toContain("mondo");
    expect(s).toEqual([...s].sort());
    expect(s.length).toBeGreaterThanOrEqual(50);
  });

  it("exposes camelCase metadata with modes as arrays", () => {
    const info = sourceInfo();
    const byKey = new Map(info.map((r) => [r.key, r]));

    const mondo = byKey.get("mondo");
    expect(mondo?.modes).toEqual(["pattern", "cache", "remote"]);
    expect(byKey.get("drugbank")?.modes).toEqual(["pattern"]);
    expect(byKey.get("hgnc")?.modes).toEqual(["pattern", "cache", "remote"]);

    expect(Object.keys(mondo ?? {}).sort()).toEqual([
      "example",
      "key",
      "modes",
      "name",
      "speciesAware",
      "versionAware",
    ]);
  });

  it("every source has an example", () => {
    for (const row of sourceInfo()) {
      expect(row.example, `${row.key} has an example`).toBeTruthy();
    }
  });
});
