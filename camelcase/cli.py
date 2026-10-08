"""Command line: humpy trek | haul | camel | grunt"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .art import CAMEL
from .case import to_camel, to_pascal, to_snake
from .haul import haul
from .report import haul_terminal, markdown, terminal
from .trek import trek


def _color(choice: str) -> bool:
    if choice == "always":
        return True
    if choice == "never" or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="humpy", description="A camel who walks your repo at night.")
    parser.add_argument("--version", action="version", version=f"humpy {__version__}")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    commands = parser.add_subparsers(dest="command", required=True)

    t = commands.add_parser("trek", help="walk a folder: buried markers, dropped keys, snakes, missing basics")
    t.add_argument("path", nargs="?", default=".")
    t.add_argument("--json", action="store_true", help="print the raw findings as JSON")
    t.add_argument("--md", metavar="FILE", help="also append a Markdown report to FILE (for example $GITHUB_STEP_SUMMARY)")
    t.add_argument("--fail-under", type=int, default=0, metavar="N", help="exit with 1 when the score is below N")
    t.add_argument("--no-snakes", action="store_true", help="do not count snake_case names")

    h = commands.add_parser("haul", help="carry back the open issues of owner/name")
    h.add_argument("repo")
    h.add_argument("--limit", type=int, default=100)
    h.add_argument("--json", action="store_true")

    c = commands.add_parser("camel", help="snake_case -> camelCase (it is in the name)")
    c.add_argument("names", nargs="+")
    c.add_argument("--style", choices=("camel", "pascal", "snake"), default="camel")

    commands.add_parser("grunt", help="he says hello. sort of.")
    return parser


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    color = _color(args.color)
    if args.command == "grunt":
        print(CAMEL.format(version=__version__))
        return 0
    if args.command == "camel":
        fn = {"camel": to_camel, "pascal": to_pascal, "snake": to_snake}[args.style]
        print("\n".join(fn(n) for n in args.names))
        return 0
    if args.command == "trek":
        try:
            report = trek(args.path, snakes=not args.no_snakes)
        except NotADirectoryError as error:
            print(f"humpy: {error}", file=sys.stderr)
            return 2
        print(json.dumps(report.to_dict(), indent=2) if args.json else terminal(report, color))
        if args.md:
            with open(args.md, "a", encoding="utf-8") as handle:
                handle.write(markdown(report))
        return 1 if report.score < args.fail_under else 0
    try:
        result = haul(args.repo, limit=args.limit)
    except (ValueError, LookupError, PermissionError) as error:
        print(f"humpy: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.json else haul_terminal(result, color))
    return 0
