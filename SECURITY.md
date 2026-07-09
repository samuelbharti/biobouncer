# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately. Open a GitHub security advisory
on this repository, or contact the maintainer. Do not open a public issue for a
security problem.

## Keeping secrets out of the repository

- The default `pattern` and `cache` modes need no secrets. Only optional
  remote-mode API access uses them.
- Put local values in `.env`, which is gitignored. Use `.env.example` as the
  template.
- The `.gitignore` ignores whole categories and directories (for example
  `secrets/`, `*.key`, `*.pem`, `.env`) so that no individually sensitive
  filename has to be listed in a tracked file.
- For a file whose name itself would reveal something sensitive, add it to
  `.git/info/exclude`. That file is local and never committed.
- Two backstops run automatically. The `detect-private-key` and
  `detect-aws-credentials` hooks run locally on every commit, and gitleaks scans
  the full history in CI.
