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
});
