# biobouncer (JavaScript / TypeScript)

Validate biological identifiers and inputs, the same way and with the same
verdict as the [R and Python packages](https://github.com/samuelbharti/biobouncer).
One small API checks gene symbols, ontology terms, variant formats, and database
identifiers across 50 sources, and returns a result that matches the other two
packages, enforced by a shared conformance corpus.

This is the JavaScript/TypeScript implementation. It is part of the biobouncer
monorepo and shares its identifier spec and corpus with the R and Python
packages.

**Documentation:** [API reference](https://www.samuelbharti.com/biobouncer/js/),
generated from the TypeScript types. The
[R](https://www.samuelbharti.com/biobouncer/r/) and
[Python](https://www.samuelbharti.com/biobouncer/py/) docs cover the same API.

> **Status:** in development, not yet published to npm.

## Install

Not on npm yet. From the checkout:

```sh
npm --prefix pkg-js run build
```

## Quickstart

```ts
import { checkId, isValidId, report } from "biobouncer";

// pattern mode: is the string well-formed? (offline, synchronous)
isValidId("MONDO:0005148", "mondo"); // true
isValidId("mondo:5148", "mondo"); // false

// A rich, per-item result
checkId("mondo:5148", "mondo")[0];
// { input: "mondo:5148", valid: false, suggestion: "MONDO:0005148", ... }
```

## Clean a column

`report()` validates a whole column; `Report.repair()` substitutes the fixable
values (a retired symbol becomes its successor, a mis-cased id its canonical
form) and leaves valid, unmappable, and missing values unchanged.

```ts
const genes = ["TP53", "MLL", "mondo:5148", null];
const r = report(genes, "hgnc", { how: "cache", version: "sample" });
r.summary; // { total: 4, valid: ..., repairable: ..., ... }
r.repair(); // ["TP53", "KMT2A", ...]
```

## Modes

- `pattern` (default): offline shape check.
- `cache`: offline existence against a bundled snapshot.
- `remote`: live existence against the source API.
- `existence`: snapshot if available, else remote, else pattern.

`pattern` and `cache` are synchronous. **A check that needs the network is
asynchronous**: `remote` mode, and `existence` mode when no installed snapshot
answers it and the source has a resolver. Use the async entry points for those:

```ts
import { checkIdAsync, isValidIdAsync } from "biobouncer";

await isValidIdAsync("P04637", "uniprot", { how: "remote", species: "homo_sapiens" });
```

The remote transport is injectable, so you can route every call through your own
HTTP client (retries, auth, proxy):

```ts
import { setRemoteTransport } from "biobouncer";
setRemoteTransport({ get: async (url) => ({ status: 200, body: await myGet(url) }), post: async () => ({ status: 200, body: null }) });
```

## Runtime targets (Node and the browser)

The package ships two builds and modern bundlers pick the right one automatically
through the `browser` export condition, so the same `import "biobouncer"` works on
the server and in the client.

- **Node and server runtimes** (Node, Bun, Deno, Next.js server components and API
  routes, Electron main): all four modes, including `cache`, which reads bundled
  snapshots from disk.
- **The browser** (React, Vite, Next.js client components, any bundler targeting
  the web): `pattern` (pure logic) and `remote` (via `fetch`) work. `cache` needs
  a filesystem, so it is not available client-side: `cache` throws a clear error
  and `snapshots()` returns an empty list rather than breaking the build. Put
  existence checks that need a snapshot on the server, or use `remote`.

It is authored in TypeScript and ships type declarations, so a `.ts`/`.tsx`
project gets full types and autocomplete. There is no browser-only setup: the
browser build has no Node builtins, so a client bundle never fails to resolve
`node:fs` and friends.

## Framework integration (Standard Schema)

`idSchema()` returns a [Standard Schema](https://standardschema.dev) validator, so
it plugs into Zod, Valibot, ArkType, and anything else that speaks the spec:

```ts
import { idSchema } from "biobouncer";
const schema = idSchema("mondo");
await schema["~standard"].validate("MONDO:0005148"); // { value: "MONDO:0005148" }
```

## Names

The API is idiomatic camelCase (`checkId`, `isValidId`, `sourceInfo`;
`Result.sourceDb`). Serialized output keeps the shared snake_case schema field
names, so JSON produced here matches R and Python. Function map:

| Python / R | JavaScript |
| --- | --- |
| `check_id` | `checkId` (+ `checkIdAsync` for remote) |
| `is_valid_id` | `isValidId` (+ `isValidIdAsync`) |
| `report` / `report_id` | `report` -> `Report` (+ `reportAsync`) |
| `synthesize` / `synthesize_ids` | `synthesize` |
| `snapshots` / `biobouncer_snapshots` | `snapshots` |
| `cache_dir` / `biobouncer_cache_dir` | `cacheDir` |

See the runnable
[`demo/biobouncer_js.mjs`](https://github.com/samuelbharti/biobouncer/blob/main/demo/biobouncer_js.mjs)
for the full tour.
