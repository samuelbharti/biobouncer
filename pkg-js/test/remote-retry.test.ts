// The default transport retries a failed request, not only a transient status.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, afterEach, describe, expect, it } from "vitest";
import { checkIdAsync } from "../src/core";
import { resetRemoteTransport } from "../src/remote";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-retry-"));

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
});
afterAll(() => resetRemoteTransport());

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("remote retry", () => {
  it("recovers when the first request fails at the network level", async () => {
    resetRemoteTransport();
    let calls = 0;
    globalThis.fetch = async () => {
      calls++;
      if (calls === 1) throw new TypeError("fetch failed");
      return jsonResponse(200, { page: { totalElements: 1 } });
    };

    const r = await checkIdAsync("MONDO:0005148", "mondo", {
      how: "remote",
      refresh: true,
    });
    expect(r[0]?.valid).toBe(true);
    expect(calls).toBe(2);
  });

  it("retries a transient status and returns the last response", async () => {
    resetRemoteTransport();
    let calls = 0;
    globalThis.fetch = async () => {
      calls++;
      if (calls < 3) return jsonResponse(503, null);
      return jsonResponse(200, { page: { totalElements: 1 } });
    };

    const r = await checkIdAsync("MONDO:0005148", "mondo", {
      how: "remote",
      refresh: true,
    });
    expect(r[0]?.valid).toBe(true);
    expect(calls).toBe(3);
  });
});
