# Contributing to biogate

Thanks for helping. This guide covers the workflow and the local tooling.

## Repository layout

- `shared/` is the single source of truth: source definitions and the
  conformance corpus.
- `r/` is the R package. `python/` is the Python package.
- `tools/sync_shared.py` vendors `shared/` into each package.
- `PLAN.md` has the architecture and the phased plan. `CLAUDE.md` is the short
  conventions digest.

## Branches and commits

- `main` is protected. Do not commit to it directly. Open a pull request.
- Name branches with a type prefix: `feat/<slug>`, `fix/<slug>`, or
  `chore/<slug>`.
- Use Conventional Commit messages, for example `feat: add efo pattern`. Keep
  commits small and focused. The commit-msg hook checks the format.
- The PR title also follows Conventional Commits. A CI check enforces it.

## Local setup

Install the git hooks once:

```sh
prek install --install-hooks
prek install --hook-type commit-msg
```

Then before every push:

```sh
prek run --all-files
```

The hooks run air (R formatting), ruff (Python lint and format), and a set of
general checks. R work also runs `R CMD check` and lintr in CI; Python work runs
ruff and pytest in CI.

## Editing the shared spec

Edit files under `shared/`, never the vendored copies under `r/inst/extdata/` or
`python/src/biogate/_data/`. After editing, run:

```sh
python tools/sync_shared.py
```

The drift CI job fails if the vendored copies do not match a fresh sync.

## Secrets

Never commit secrets. Put local values in `.env` (gitignored) using
`.env.example` as a template. For a file whose name is itself sensitive, add it
to `.git/info/exclude`, which is never committed, rather than to `.gitignore`.
See `SECURITY.md`.
