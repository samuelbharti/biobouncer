// The biobouncer demo in JavaScript. It runs the same story as the Python and R
// notebooks, over the same messy data, so all three return the same answers.
//
// Run it from the repo root after building the package:
//   npm --prefix pkg-js run build && node demo/biobouncer_js.mjs
// or:  python tools/run_demo.py js
//
// It imports the built package from ../pkg-js/dist, reads the shared demo data,
// and guards remote mode so it runs offline too.

import { readFileSync } from "node:fs";
import {
  cacheDir,
  checkId,
  checkIdAsync,
  idSchema,
  isValidId,
  report,
  snapshots,
  sourceInfo,
  sources,
  version,
} from "../pkg-js/dist/index.js";

function heading(title) {
  console.log(`\n=== ${title} ===`);
}

function readCsv(name) {
  const text = readFileSync(new URL(`./data/${name}`, import.meta.url), "utf8");
  const lines = text.trim().split(/\r?\n/);
  const cols = (lines.shift() ?? "").split(",");
  return lines.map((line) => {
    const vals = line.split(",");
    return Object.fromEntries(cols.map((c, i) => [c, vals[i] ?? ""]));
  });
}

// A cell is "missing" when the source value is blank.
const cell = (v) => (v === "" ? null : v);

const associations = readCsv("associations.csv");
const identifiers = readCsv("identifiers.csv");

// 1. Discover ----------------------------------------------------------------
heading("1. Discover");
console.log(`biobouncer ${version}: ${sources().length} sources supported`);
for (const row of sourceInfo().filter((s) => ["mondo", "hgnc", "go"].includes(s.key))) {
  console.log(`  ${row.key}: e.g. ${row.example} (${row.modes.join(", ")})`);
}

// 2. Snapshots ---------------------------------------------------------------
heading("2. Snapshots (bundled offline data)");
console.log(`cache dir: ${cacheDir()}`);
for (const s of snapshots().filter((row) => row.version === "sample").slice(0, 4)) {
  console.log(`  ${s.source} @ ${s.version}: ${s.nIds} ids (${s.location})`);
}

// 3. pattern mode: is the string well-formed? --------------------------------
heading("3. pattern mode (offline shape check)");
for (const id of ["MONDO:0005148", "mondo:5148", "MONDO:banana"]) {
  const r = checkId(id, "mondo", { how: "pattern" })[0];
  console.log(`  ${id.padEnd(16)} valid=${r.valid} suggestion=${r.suggestion ?? "-"}`);
}

// 4. cache mode: does the id exist? repair renamed and obsolete ids ----------
heading("4. cache mode (offline existence + repair)");
for (const [col, src] of [
  ["gene", "hgnc"],
  ["disease", "mondo"],
  ["process", "go"],
]) {
  const column = associations.map((r) => cell(r[col]));
  const rep = report(column, src, { how: "cache", version: "sample" });
  console.log(`  ${col} -> ${src}: ${rep.toString()}`);
  console.log(`    repaired: ${JSON.stringify(rep.repair())}`);
}

// 5. pattern across many sources ---------------------------------------------
heading("5. pattern across many sources");
for (const row of identifiers) {
  const valid = isValidId(row.value, row.source_db, { how: "pattern" });
  console.log(
    `  ${row.source_db.padEnd(8)} ${String(row.value).padEnd(24)} valid=${valid}  (${row.note})`,
  );
}

// 6. remote mode: a live API check, guarded for offline ----------------------
heading("6. remote mode (live, skips cleanly offline)");
try {
  const human = (
    await checkIdAsync("P04637", "uniprot", { how: "remote", species: "homo_sapiens" })
  )[0];
  const mouse = (
    await checkIdAsync("P04637", "uniprot", { how: "remote", species: "mus_musculus" })
  )[0];
  console.log(`  P04637 as human: valid=${human.valid}`);
  console.log(`  P04637 as mouse: valid=${mouse.valid} (same id, wrong species)`);
} catch (e) {
  console.log(`  skipped (no network): ${e instanceof Error ? e.message : String(e)}`);
}

// 7. Framework integration: the Standard Schema adapter ----------------------
heading("7. Standard Schema adapter (Zod / Valibot / ArkType)");
const schema = idSchema("mondo");
for (const value of ["MONDO:0005148", "mondo:5148"]) {
  const result = await schema["~standard"].validate(value);
  const verdict = "issues" in result ? (result.issues[0]?.message ?? "invalid") : "ok";
  console.log(`  ${value.padEnd(16)} -> ${verdict}`);
}

console.log("\ndone.");
