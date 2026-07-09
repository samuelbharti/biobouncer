# CLAUDE.md

Conventions for anyone (human or agent) working in this repo. This is a short
digest. `PLAN.md` has the full architecture and the phased task list.

## What biogate is

A cross-language validator for biological identifiers. One monorepo: the R
package lives in `pkg-r/`, the Python package in `pkg-py/`, and the shared spec in
`shared/`. R and Python must return the same verdict for the same input, which is
enforced by the conformance corpus in `shared/corpus/`.

## Ground rules

- Pure R and pure Python. No Rust and no compiled extensions. Vectorize instead.
- Never hard-code an identifier pattern outside `shared/sources/`.
- Never edit a vendored copy by hand (`pkg-r/inst/extdata/`,
  `pkg-py/src/biogate/_data/`). Edit `shared/` and run
  `python tools/sync_shared.py`. The drift CI job enforces this.
- Every extrinsic result (cache or remote mode) must carry its version or
  timestamp.
- Adapters wrap the core classifier. Never duplicate validation logic.
- The default test suite must run fully offline. Remote-mode tests are opt-in.
- Preserve input order and length. Errors are explicit, never a silent FALSE.

## Working in git

- Do not commit on `main`. It is protected. Every change goes through a branch and
  a pull request.
- Branch names use a `feat/`, `fix/`, or `chore/` prefix.
- Commit messages and PR titles follow Conventional Commits, for example
  `feat: add mondo source`. Commit in small, focused batches.
- Do not attribute an AI as author or co-author on commits.

## Documentation style

- No em dashes. Write plain, direct sentences. Avoid AI writing style.

## Before you push

- Run `prek run --all-files`. Install the hooks once with
  `prek install --install-hooks` and `prek install --hook-type commit-msg`.
