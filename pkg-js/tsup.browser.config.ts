import { resolve } from "node:path";
import { defineConfig } from "tsup";

// The browser bundle. It shares every source file with the Node build except the
// io seam: this esbuild plugin rewrites the "./io" import (used by cache.ts and
// remote.ts) to io.browser.ts, the filesystem-free stub. With platform "browser",
// esbuild fails the build if any node builtin survives, so a stray node:fs import
// cannot slip into the browser output unnoticed.
const aliasBrowserIo = {
  name: "alias-browser-io",
  setup(build: {
    onResolve(opts: { filter: RegExp }, cb: () => { path: string }): void;
  }): void {
    build.onResolve({ filter: /^\.\/io$/ }, () => ({
      path: resolve("src/io.browser.ts"),
    }));
  },
};

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: false,
  splitting: false,
  clean: false,
  sourcemap: true,
  platform: "browser",
  target: "es2022",
  outDir: "dist/browser",
  esbuildPlugins: [aliasBrowserIo],
});
