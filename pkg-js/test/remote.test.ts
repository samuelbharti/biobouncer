// Remote conformance: run the shared remote corpus offline against recorded
// fixtures, mirroring pkg-py/tests/test_remote_conformance.py. A GET is keyed by
// URL alone; the Open Targets POST is keyed by (url, ensemblId from the body).

import { mkdtempSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, describe, expect, it } from "vitest";
import { checkIdAsync } from "../src/core";
import {
  type RemoteResponse,
  resetRemoteTransport,
  setRemoteTransport,
} from "../src/remote";

process.env.BIOBOUNCER_CACHE_DIR = mkdtempSync(join(tmpdir(), "biobouncer-remote-"));

const here = dirname(fileURLToPath(import.meta.url));
const dataDir = join(here, "..", "src", "_data");
const corpusDir = join(dataDir, "corpus", "remote");
const fixturesDir = join(dataDir, "fixtures", "remote");

interface Fixture {
  url: string;
  id?: string;
  status: number;
  body: unknown | null;
}

function fixtureKey(url: string, id: string | null): string {
  return `${url}${id ?? ""}`;
}

function buildIndex(): Map<string, Fixture> {
  const index = new Map<string, Fixture>();
  for (const rel of readdirSync(fixturesDir, { recursive: true })) {
    const name = String(rel);
    if (!name.endsWith(".json")) continue;
    const fx = JSON.parse(readFileSync(join(fixturesDir, name), "utf8")) as Fixture;
    index.set(fixtureKey(fx.url, fx.id ?? null), fx);
  }
  return index;
}

const INDEX = buildIndex();

function serve(url: string, id: string | null): RemoteResponse {
  const fx = INDEX.get(fixtureKey(url, id));
  if (fx === undefined)
    throw new Error(`missing fixture for url ${url} id ${String(id)}`);
  return { status: fx.status, body: fx.body };
}

setRemoteTransport({
  get: async (url) => serve(url, null),
  post: async (url, body) => {
    const id = (JSON.parse(body) as { variables: { ensemblId: string } }).variables
      .ensemblId;
    return serve(url, id);
  },
});

afterAll(() => resetRemoteTransport());

interface Case {
  input: string;
  source_db: string;
  species?: string | number | null;
  on_error?: "raise" | "indeterminate";
  expect: {
    valid?: boolean | null;
    normalized?: string;
    suggestion?: string;
    error?: boolean;
  };
}

function loadCases(): Case[] {
  const cases: Case[] = [];
  for (const f of readdirSync(corpusDir)
    .filter((n) => n.endsWith(".jsonl"))
    .sort()) {
    for (const line of readFileSync(join(corpusDir, f), "utf8").split(/\r?\n/)) {
      const t = line.trim();
      if (t) cases.push(JSON.parse(t) as Case);
    }
  }
  return cases;
}

const CASES = loadCases();

describe("remote conformance", () => {
  it("the remote corpus is not empty", () => {
    expect(CASES.length).toBeGreaterThan(0);
  });

  it.each(CASES)("$source_db $input", async (c) => {
    const results = await checkIdAsync(c.input, c.source_db, {
      how: "remote",
      species: c.species ?? null,
      onError: c.on_error ?? "raise",
    });
    const r = results[0];
    if (r === undefined) throw new Error("expected one result");
    expect(r.valid).toBe(c.expect.valid ?? null);
    expect(r.normalized).toBe(c.expect.normalized ?? null);
    expect(r.suggestion).toBe(c.expect.suggestion ?? null);
    if (c.expect.error) {
      expect(r.error).not.toBeNull();
    } else {
      expect(r.error).toBeNull();
    }
  });
});
