// Remote mode: live existence checks against source web services, ported from
// pkg-py/src/biobouncer/_remote.py. Network I/O is async in JS, so the remote
// path is async (checkIdAsync) while the offline modes stay synchronous.
//
// The transport is injectable: the default uses global fetch; the conformance
// suite injects a fixture-backed transport. Only inputs that pass the offline
// grammar (or a grammar-valid suggestion candidate) are ever looked up.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { cacheDir } from "./cache";
import { NoResolverError, RemoteError } from "./errors";
import { matches, speciesOk, suggest } from "./pattern";
import type { SourceSpec } from "./registry";

/** A single HTTP response: an integer status and the parsed JSON body (or null). */
export interface RemoteResponse {
  status: number;
  body: unknown | null;
}

/** The injectable transport. Resolvers rely only on status and parsed body. */
export interface RemoteTransport {
  get(url: string, timeout?: number): Promise<RemoteResponse>;
  post(url: string, body: string, timeout?: number): Promise<RemoteResponse>;
}

// ---------------------------------------------------------------------------
// Default transport (global fetch), with tolerant JSON parsing and light retry.
// ---------------------------------------------------------------------------

const TRANSIENT = new Set([429, 500, 502, 503, 504]);
const MAX_ATTEMPTS = 3;

async function parseBody(res: Response): Promise<unknown | null> {
  const text = await res.text();
  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function fetchOnce(
  method: "GET" | "POST",
  url: string,
  body: string | undefined,
  timeout: number,
): Promise<RemoteResponse> {
  const headers: Record<string, string> = {
    "User-Agent": "biobouncer",
    Accept: "application/json",
  };
  if (method === "POST") headers["Content-Type"] = "application/json";
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout * 1000);
  try {
    const res = await fetch(url, { method, headers, body, signal: controller.signal });
    return { status: res.status, body: await parseBody(res) };
  } catch (e) {
    throw new RemoteError(`request to ${url} failed: ${String(e)}`);
  } finally {
    clearTimeout(timer);
  }
}

async function withRetry(fn: () => Promise<RemoteResponse>): Promise<RemoteResponse> {
  let last: RemoteResponse | null = null;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    const res = await fn();
    if (!TRANSIENT.has(res.status)) return res;
    last = res;
    await new Promise((r) => setTimeout(r, 500 * 2 ** attempt));
  }
  if (last === null) throw new RemoteError("no response");
  return last;
}

const defaultTransport: RemoteTransport = {
  get: (url, timeout = 30) =>
    withRetry(() => fetchOnce("GET", url, undefined, timeout)),
  post: (url, body, timeout = 30) =>
    withRetry(() => fetchOnce("POST", url, body, timeout)),
};

let activeTransport: RemoteTransport = defaultTransport;

/** Replace the HTTP transport (used by tests to serve recorded fixtures). */
export function setRemoteTransport(t: RemoteTransport): void {
  activeTransport = t;
}

/** Restore the default fetch-based transport. */
export function resetRemoteTransport(): void {
  activeTransport = defaultTransport;
}

// ---------------------------------------------------------------------------
// Resolvers
// ---------------------------------------------------------------------------

interface Resolver {
  name: string;
  url(spec: SourceSpec, id: string): string;
  exists(status: number, body: unknown): boolean;
  body?(spec: SourceSpec, id: string): string;
  speciesOk?(
    spec: SourceSpec,
    id: string,
    body: unknown,
    species: string | number | null,
  ): boolean;
  retired?(spec: SourceSpec, body: unknown): [boolean, string | null];
}

function conf(spec: SourceSpec): Record<string, unknown> {
  return (spec.remote ?? {}) as Record<string, unknown>;
}

function obj(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

function existsBy404(status: number): boolean {
  if (status === 200) return true;
  if (status === 404) return false;
  throw new RemoteError(`remote source returned unexpected status ${status}`);
}

/** Take the substring after the last "/", then turn the first "_" into ":". */
function normalizeObo(value: unknown): string | null {
  if (typeof value !== "string" || value === "") return null;
  const tail = value.slice(value.lastIndexOf("/") + 1);
  return tail.replace("_", ":");
}

function statusOnly(
  name: string,
  url: (spec: SourceSpec, id: string) => string,
): Resolver {
  return { name, url, exists: existsBy404 };
}

// OLS (16 ontologies)
function olsOboId(spec: SourceSpec, id: string): string {
  const prefix = conf(spec).obo_prefix;
  if (typeof prefix === "string" && prefix)
    return `${prefix}:${id.split(":").slice(1).join(":") || id}`;
  return id;
}
function olsCount(body: unknown): number {
  const page = obj(obj(body).page);
  const n = Number(page.totalElements);
  return Number.isFinite(n) ? n : 0;
}
function olsTerm(body: unknown): Record<string, unknown> | null {
  const terms = obj(obj(body)._embedded).terms;
  if (Array.isArray(terms) && terms.length > 0) return obj(terms[0]);
  return null;
}

const RESOLVERS: Record<string, Resolver> = {
  ols: {
    name: "ols",
    url: (spec, id) =>
      `https://www.ebi.ac.uk/ols4/api/ontologies/${String(conf(spec).ols_ontology)}/terms?obo_id=${olsOboId(spec, id)}`,
    exists: (status, body) => {
      if (status === 200) return olsCount(body) >= 1;
      if (status === 404) return false;
      throw new RemoteError(`OLS returned unexpected status ${status}`);
    },
    retired: (_spec, body) => {
      const term = olsTerm(body);
      if (term?.is_obsolete) return [true, normalizeObo(term.term_replaced_by)];
      return [false, null];
    },
  },

  ensembl: {
    name: "ensembl",
    url: (_spec, id) =>
      `https://rest.ensembl.org/lookup/id/${id}?content-type=application/json`,
    exists: (status) => {
      if (status === 200) return true;
      if (status === 400 || status === 404) return false;
      throw new RemoteError(`Ensembl returned unexpected status ${status}`);
    },
    speciesOk: (spec, id, _body, species) => speciesOk(spec, id, species),
  },

  uniprot: {
    name: "uniprot",
    url: (_spec, id) => `https://rest.uniprot.org/uniprotkb/${id}.json`,
    exists: (status, body) => {
      if (status === 200) {
        const t = obj(body).entryType;
        return typeof t === "string" && t.startsWith("UniProtKB");
      }
      if (status === 404) return false;
      throw new RemoteError(`UniProt returned unexpected status ${status}`);
    },
    speciesOk: (spec, _id, body, species) => uniprotSpeciesOk(spec, body, species),
  },

  mutalyzer: {
    name: "mutalyzer",
    url: (_spec, id) => `https://mutalyzer.nl/api/normalize/${encodeURIComponent(id)}`,
    exists: (status) => {
      if (status === 200) return true;
      if (status === 422) return false;
      throw new RemoteError(`Mutalyzer returned unexpected status ${status}`);
    },
  },

  dbsnp: {
    name: "dbsnp",
    url: (_spec, id) => {
      const number = id.slice(0, 2).toLowerCase() === "rs" ? id.slice(2) : id;
      return `https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/${number}`;
    },
    exists: (status) => {
      if (status === 200) return true;
      if (status === 404) return false;
      throw new RemoteError(`dbSNP returned unexpected status ${status}`);
    },
    retired: (_spec, body) => {
      const merged = obj(obj(body).merged_snapshot_data).merged_into;
      if (Array.isArray(merged) && merged.length > 0)
        return [true, `rs${String(merged[0])}`];
      return [false, null];
    },
  },

  interpro: {
    name: "interpro",
    url: (spec, id) =>
      `https://www.ebi.ac.uk/interpro/api/entry/${String(conf(spec).interpro_db)}/${id}`,
    exists: (status) => {
      if (status === 200) return true;
      if (status === 204 || status === 404) return false;
      throw new RemoteError(`InterPro returned unexpected status ${status}`);
    },
  },

  pdb: statusOnly("pdb", (_s, id) => `https://data.rcsb.org/rest/v1/core/entry/${id}`),
  chembl: statusOnly(
    "chembl",
    (_s, id) => `https://www.ebi.ac.uk/chembl/api/data/chembl_id_lookup/${id}.json`,
  ),
  reactome: statusOnly(
    "reactome",
    (_s, id) => `https://reactome.org/ContentService/data/query/${id}`,
  ),
  rfam: statusOnly(
    "rfam",
    (_s, id) => `https://rfam.org/family/${id}?content-type=application/json`,
  ),
  uniparc: statusOnly(
    "uniparc",
    (_s, id) => `https://rest.uniprot.org/uniparc/${id}.json`,
  ),
  complexportal: statusOnly(
    "complexportal",
    (_s, id) => `https://www.ebi.ac.uk/intact/complex-ws/complex/${id}`,
  ),
  wikipathways: statusOnly(
    "wikipathways",
    (_s, id) =>
      `https://www.wikipathways.org/wikipathways-assets/pathways/${id}/${id}.gpml`,
  ),
  prosite: statusOnly("prosite", (_s, id) => `https://prosite.expasy.org/${id}`),

  refseq: {
    name: "refseq",
    url: (_spec, id) =>
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=${refseqDb(id)}&id=${id}&retmode=json`,
    exists: (status, body) => {
      if (status !== 200)
        throw new RemoteError(`RefSeq returned unexpected status ${status}`);
      const uids = obj(obj(body).result).uids;
      return Array.isArray(uids) && uids.length >= 1;
    },
  },

  clinvar: {
    name: "clinvar",
    url: (_spec, id) =>
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=${id}&retmode=json`,
    exists: (status, body) => {
      if (status !== 200)
        throw new RemoteError(`ClinVar returned unexpected status ${status}`);
      const count = Number(obj(obj(body).esearchresult).count);
      return Number.isFinite(count) && count >= 1;
    },
  },

  mirbase: {
    name: "mirbase",
    url: (_spec, id) =>
      `https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral?query=${id}&format=json`,
    exists: (status, body) => {
      if (status !== 200)
        throw new RemoteError(`EBI Search returned unexpected status ${status}`);
      const n = Number(obj(body).hitCount);
      return Number.isFinite(n) && n >= 1;
    },
  },

  genenames: {
    name: "genenames",
    url: (_spec, id) => `https://rest.genenames.org/fetch/symbol/${id}`,
    exists: (status, body) => {
      if (status === 200) {
        const resp = obj(obj(body).response);
        const found = Number(resp.numFound);
        if (!Number.isFinite(found) || found < 1) return false;
        const docs = resp.docs;
        return (
          Array.isArray(docs) &&
          docs.length > 0 &&
          String(obj(docs[0]).status) === "Approved"
        );
      }
      if (status === 404) return false;
      throw new RemoteError(`genenames returned unexpected status ${status}`);
    },
  },

  opentargets: {
    name: "opentargets",
    url: () => "https://api.platform.opentargets.org/api/v4/graphql",
    body: (_spec, id) =>
      JSON.stringify({
        query:
          "query biobouncer($ensemblId: String!) { target(ensemblId: $ensemblId) { id } }",
        variables: { ensemblId: id },
      }),
    exists: (status, body) => {
      if (status === 200) return obj(obj(body).data).target != null;
      throw new RemoteError(`Open Targets returned unexpected status ${status}`);
    },
  },
};

function refseqDb(id: string): string {
  const prefix = (id.split("_")[0] ?? "").toUpperCase();
  return ["AP", "NP", "WP", "XP", "YP", "ZP"].includes(prefix) ? "protein" : "nuccore";
}

function speciesTaxon(
  block: NonNullable<SourceSpec["species"]>,
  species: string | number,
): number | null {
  for (const entry of block.map) {
    if (String(entry.name) === String(species)) {
      return entry.taxon ?? null;
    }
  }
  if (typeof species === "number") return species;
  if (typeof species === "string" && /^[0-9]+$/.test(species)) return Number(species);
  return null;
}

function uniprotSpeciesOk(
  spec: SourceSpec,
  body: unknown,
  species: string | number | null,
): boolean {
  if (species === null) return true;
  const block = spec.species;
  if (!block) return true;
  if (block.scheme !== "uniprot_organism") return true;
  const expected = speciesTaxon(block, species);
  if (expected === null) return true;
  const bodyTaxon = obj(obj(body).organism).taxonId;
  if (bodyTaxon === undefined || bodyTaxon === null) return true;
  const got = Number(bodyTaxon);
  return Number.isFinite(got) ? got === expected : true;
}

function getResolver(spec: SourceSpec): Resolver {
  const name = conf(spec).resolver;
  const resolver = typeof name === "string" ? RESOLVERS[name] : undefined;
  if (resolver === undefined) {
    throw new NoResolverError(`no remote resolver for ${spec.key}`);
  }
  return resolver;
}

// ---------------------------------------------------------------------------
// Lookup and batch verdicts
// ---------------------------------------------------------------------------

interface Lookup {
  valid: boolean;
  successor: string | null;
  error: string | null;
}

// --- On-disk response cache (Node-only) ------------------------------------
// A remote response is cached under the cache dir so a repeat check of the same
// id does not hit the network. The cache is local and per-language; it never
// changes a verdict, which is always recomputed from the cached status and body,
// with species compared at read time. An indeterminate response is never cached.

function safeIdent(id: string): string {
  return id.replace(/[^A-Za-z0-9._-]/g, "_");
}

function redactUrl(url: string): string {
  return url.replace(/([?&](?:api_key|email)=)[^&]*/g, "$1REDACTED");
}

function remoteTtlSeconds(): number {
  const v = Number(process.env.BIOBOUNCER_REMOTE_TTL);
  return Number.isFinite(v) ? v : 0;
}

function isStale(fetchedAt: unknown): boolean {
  const ttl = remoteTtlSeconds();
  if (ttl <= 0) return false;
  if (typeof fetchedAt !== "string") return true;
  const t = Date.parse(fetchedAt);
  if (Number.isNaN(t)) return true;
  return (Date.now() - t) / 1000 > ttl;
}

function cachePathFor(resolver: Resolver, id: string): string {
  return join(cacheDir(), "remote", resolver.name, `${safeIdent(id)}.json`);
}

function readRemoteCache(path: string): { status: number; body: unknown } | null {
  try {
    if (!existsSync(path)) return null;
    const rec = JSON.parse(readFileSync(path, "utf8")) as {
      status: number;
      body: unknown;
      fetched_at?: string;
    };
    if (isStale(rec.fetched_at)) return null;
    return { status: rec.status, body: rec.body };
  } catch {
    return null;
  }
}

function writeRemoteCache(path: string, url: string, res: RemoteResponse): void {
  try {
    mkdirSync(dirname(path), { recursive: true });
    const record = {
      status: res.status,
      body: res.body,
      url: redactUrl(url),
      fetched_at: new Date().toISOString(),
    };
    writeFileSync(path, JSON.stringify(record));
  } catch {
    // Best effort: a cache-write failure must not fail a valid lookup.
  }
}

/** Turn a (status, body) into a verdict. exists() may throw on an unexpected status. */
function verdictFrom(
  resolver: Resolver,
  spec: SourceSpec,
  id: string,
  species: string | number | null,
  status: number,
  body: unknown,
): Lookup {
  if (!resolver.exists(status, body))
    return { valid: false, successor: null, error: null };
  if (resolver.speciesOk && !resolver.speciesOk(spec, id, body, species)) {
    return { valid: false, successor: null, error: null };
  }
  if (resolver.retired) {
    const [isRetired, successor] = resolver.retired(spec, body);
    if (isRetired) return { valid: false, successor, error: null };
  }
  return { valid: true, successor: null, error: null };
}

async function remoteLookup(
  resolver: Resolver,
  spec: SourceSpec,
  id: string,
  species: string | number | null,
  onError: "raise" | "indeterminate",
  refresh: boolean,
): Promise<Lookup> {
  const url = resolver.url(spec, id);
  const cachePath = cachePathFor(resolver, id);

  if (!refresh) {
    const hit = readRemoteCache(cachePath);
    if (hit !== null)
      return verdictFrom(resolver, spec, id, species, hit.status, hit.body);
  }

  try {
    const res = resolver.body
      ? await activeTransport.post(url, resolver.body(spec, id))
      : await activeTransport.get(url);
    // exists() runs before the write, so an unexpected status is never cached.
    const lookup = verdictFrom(resolver, spec, id, species, res.status, res.body);
    writeRemoteCache(cachePath, url, res);
    return lookup;
  } catch (e) {
    if (e instanceof RemoteError && onError === "indeterminate") {
      return { valid: false, successor: null, error: e.message };
    }
    throw e;
  }
}

/** One verdict tuple per item, in input order. */
export interface RemoteVerdict {
  valid: boolean | null;
  normalized: string | null;
  suggestion: string | null;
  error: string | null;
}

type Plan =
  | { kind: "missing" }
  | { kind: "wellformed"; id: string }
  | { kind: "malformed"; candidate: string | null };

/** Look up a batch of already-coerced items against a source's remote resolver. */
export async function remoteVerdicts(
  spec: SourceSpec,
  items: Array<string | null>,
  species: string | number | null,
  onError: "raise" | "indeterminate",
  refresh = false,
): Promise<RemoteVerdict[]> {
  const resolver = getResolver(spec);

  const plans: Plan[] = [];
  const need = new Set<string>();
  for (const item of items) {
    if (item === null) {
      plans.push({ kind: "missing" });
    } else if (matches(spec.pattern, item)) {
      plans.push({ kind: "wellformed", id: item });
      need.add(item);
    } else {
      const candidate = suggest(spec, item);
      plans.push({ kind: "malformed", candidate });
      if (candidate !== null) need.add(candidate);
    }
  }

  const resolved = new Map<string, Lookup>();
  for (const id of [...need].sort()) {
    resolved.set(id, await remoteLookup(resolver, spec, id, species, onError, refresh));
  }

  return plans.map((plan): RemoteVerdict => {
    if (plan.kind === "missing") {
      return { valid: null, normalized: null, suggestion: null, error: null };
    }
    if (plan.kind === "wellformed") {
      const r = resolved.get(plan.id);
      if (r && r.error !== null)
        return { valid: null, normalized: null, suggestion: null, error: r.error };
      if (r?.valid)
        return { valid: true, normalized: plan.id, suggestion: null, error: null };
      return {
        valid: false,
        normalized: null,
        suggestion: r?.successor ?? null,
        error: null,
      };
    }
    // malformed: a suggestion candidate only surfaces if it exists remotely.
    if (plan.candidate !== null) {
      const r = resolved.get(plan.candidate);
      if (r?.valid)
        return {
          valid: false,
          normalized: null,
          suggestion: plan.candidate,
          error: null,
        };
    }
    return { valid: false, normalized: null, suggestion: null, error: null };
  });
}
