// The remote disk cache: a repeat lookup is served from disk without a second
// network call, and refresh bypasses it.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { checkIdAsync } from "../src/core";
import {
  type RemoteResponse,
  resetRemoteTransport,
  setRemoteTransport,
} from "../src/remote";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-rcache-"));

afterAll(() => resetRemoteTransport());

describe("remote disk cache", () => {
  it("reuses a cached lookup and lets refresh bypass it", async () => {
    let calls = 0;
    setRemoteTransport({
      get: async (): Promise<RemoteResponse> => {
        calls++;
        return { status: 200, body: { page: { totalElements: 1 } } };
      },
      post: async (): Promise<RemoteResponse> => {
        calls++;
        return { status: 200, body: {} };
      },
    });

    const first = await checkIdAsync("MONDO:0005148", "mondo", { how: "remote" });
    expect(first[0]?.valid).toBe(true);
    expect(calls).toBe(1);

    const second = await checkIdAsync("MONDO:0005148", "mondo", { how: "remote" });
    expect(second[0]?.valid).toBe(true);
    expect(calls).toBe(1); // served from the cache

    const refreshed = await checkIdAsync("MONDO:0005148", "mondo", {
      how: "remote",
      refresh: true,
    });
    expect(refreshed[0]?.valid).toBe(true);
    expect(calls).toBe(2); // refresh bypasses the cache
  });
});
