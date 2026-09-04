import { defineConfig } from "tsup";

// Dual ESM + CJS with type declarations. Splitting is off so each entry emits a
// single flat file, which keeps the runtime data-path resolution (a sibling
// _data directory) predictable in both dev and the published dist.
export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  splitting: false,
  clean: true,
  sourcemap: true,
  target: "node20",
  // Provide import.meta.url in the CJS output (and __dirname in ESM), so the
  // runtime resolves the sibling _data/snapshots directory in both formats.
  shims: true,
});
