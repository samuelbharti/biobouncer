# biobouncer (JavaScript / TypeScript)

Validate biological identifiers and inputs, the same way and with the same
verdict as the [R and Python packages](https://github.com/samuelbharti/biobouncer).
One small API checks gene symbols, ontology terms, variant formats, and database
identifiers across 50 sources, and returns a result that matches the other two
packages, enforced by a shared conformance corpus.

This is the JavaScript/TypeScript implementation. It is part of the biobouncer
monorepo and shares its identifier spec and corpus with the R and Python
packages.

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

`pattern` and `cache` are synchronous. **`remote` is asynchronous** (network I/O),
so use the async entry points:

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

See the runnable [`demo/biobouncer_js.mjs`](../demo/biobouncer_js.mjs) for the
full tour.
