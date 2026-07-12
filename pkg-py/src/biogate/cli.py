"""Command-line interface for biogate.

Installed as the ``biogate`` command. It validates identifiers from arguments,
files, or standard input, and exits non-zero if any input is invalid, so it
drops into shell pipelines and CI checks.

Examples:
    biogate check --source mondo MONDO:0005148 mondo:5148
    biogate check --source mondo --file ids.txt
    cat ids.txt | biogate check --source mondo
    biogate sources
    biogate info --source mondo
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, check_id, source_info, sources

_MODES = ("pattern", "cache", "remote", "existence")


def _gather_ids(args: argparse.Namespace) -> list[str]:
    """Collect ids from positional arguments, files, and stdin, in that order."""
    ids: list[str] = list(args.ids)
    for path in args.file or []:
        if path == "-":
            text = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        ids += [line.strip() for line in text.splitlines() if line.strip()]
    # Read piped stdin only when nothing else was given, and never from a tty.
    if not ids and not args.file:
        try:
            if not sys.stdin.isatty():
                ids += [
                    line.strip()
                    for line in sys.stdin.read().splitlines()
                    if line.strip()
                ]
        except (OSError, ValueError):
            pass
    return ids


def _print_check(results, fmt: str, invalid_only: bool) -> None:
    rows = [r for r in results if not r.valid] if invalid_only else results
    if fmt == "json":
        print(
            json.dumps(
                [
                    {
                        "input": r.input,
                        "valid": r.valid,
                        "normalized": r.normalized,
                        "suggestion": r.suggestion,
                        "source_db": r.source_db,
                        "how": r.how,
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
        return
    if fmt == "tsv":
        print("input\tvalid\tnormalized\tsuggestion")
        for r in rows:
            print(
                f"{r.input}\t{str(r.valid).lower()}\t"
                f"{r.normalized or ''}\t{r.suggestion or ''}"
            )
        return
    for r in rows:
        mark = "ok  " if r.valid else "FAIL"
        extra = ""
        if r.valid and r.normalized and r.normalized != r.input:
            extra = f"  -> {r.normalized}"
        elif not r.valid and r.suggestion:
            extra = f"  did you mean {r.suggestion}?"
        print(f"{mark}  {r.input}{extra}")


def _cmd_check(args: argparse.Namespace) -> int:
    ids = _gather_ids(args)
    if not ids:
        print("biogate check: no identifiers given", file=sys.stderr)
        return 2
    results = check_id(
        ids,
        source_db=args.source,
        how=args.how,
        species=args.species,
        version=args.version,
        refresh=args.refresh,
    )
    _print_check(results, args.format, args.invalid_only)
    n_invalid = sum(not r.valid for r in results)
    if not args.quiet and n_invalid:
        print(
            f"{n_invalid} of {len(results)} invalid for {args.source} "
            f"({args.how} mode)",
            file=sys.stderr,
        )
    return 1 if n_invalid else 0


def _cmd_sources(args: argparse.Namespace) -> int:
    for key in sources():
        print(key)
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    rows = source_info()
    if args.source:
        rows = [r for r in rows if r["key"] == args.source]
        if not rows:
            print(f"biogate info: unknown source {args.source!r}", file=sys.stderr)
            return 2
    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return 0
    print("key\tname\texample\tmodes\tspecies_aware")
    for r in rows:
        print(
            f"{r['key']}\t{r['name']}\t{r['example']}\t"
            f"{','.join(r['modes'])}\t{str(r['species_aware']).lower()}"
        )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biogate",
        description="Validate biological identifiers from the command line.",
    )
    parser.add_argument("--version", action="version", version=f"biogate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate identifiers against a source")
    check.add_argument("ids", nargs="*", help="identifiers to check")
    check.add_argument("-s", "--source", required=True, help="source key, e.g. mondo")
    check.add_argument("--how", choices=_MODES, default="pattern", help="checking mode")
    check.add_argument("--species", default=None, help="species name or taxon id")
    check.add_argument("--version", dest="version", default=None, help="source version")
    check.add_argument(
        "--refresh",
        action="store_true",
        help="re-fetch remote checks, ignoring any cached response",
    )
    check.add_argument(
        "-f",
        "--file",
        action="append",
        help="read ids from a file, one per line; - for stdin",
    )
    check.add_argument(
        "--format",
        choices=("text", "tsv", "json"),
        default="text",
        help="output format",
    )
    check.add_argument(
        "--invalid-only", action="store_true", help="print only invalid inputs"
    )
    check.add_argument(
        "-q", "--quiet", action="store_true", help="suppress the summary line"
    )
    check.set_defaults(func=_cmd_check)

    src = sub.add_parser("sources", help="list available source keys")
    src.set_defaults(func=_cmd_sources)

    info = sub.add_parser("info", help="show source metadata (example id and modes)")
    info.add_argument("-s", "--source", default=None, help="limit to one source")
    info.add_argument(
        "--format", choices=("tsv", "json"), default="tsv", help="output format"
    )
    info.set_defaults(func=_cmd_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"biogate: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
