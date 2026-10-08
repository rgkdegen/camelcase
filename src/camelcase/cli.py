"""humpy — the night-shift camel.

    humpy scan [PATH]        walk the repo, count files, sniff out issues
    humpy spit [PATH]        list every open issue humpy would spit on
    humpy camel NAME...      convert names to camelCase
    humpy lint [PATH]        report snake_case names in Python files (exit 1 if any)
    humpy graph [PATH]       print a contribution graph from `git log` (last 24h)
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import subprocess
import sys

from . import __version__
from .case import to_camel, to_pascal, to_snake
from .scan import scan

CAMEL = r"""
      |  |    |  |
      |  |    |  |    .-.
    .-'--'----'--'-.  ( o>     humpy v{v}
   (                )_/ /      night shift: {clock}
    `-.  .-''-.  .-'  /        "{quote}"
       (    )(    )
        `--'  `--'
"""
QUOTES = ["good camel.", "no water needed.", "hmph.", "i chew twice.", "the desert is just a big repo.", "spitting: newest first."]

GREEN = ["\033[38;5;254m", "\033[38;5;151m", "\033[38;5;77m", "\033[38;5;34m", "\033[38;5;22m"]
RESET = "\033[0m"
LABEL_COLOR = {"bug": "\033[31m", "todo": "\033[33m", "dead code": "\033[35m", "typo": "\033[33m", "camelcase": "\033[36m"}


def _c(s: str, color: str, on: bool) -> str:
    return f"{color}{s}{RESET}" if on else s


def _banner(on: bool) -> str:
    now = dt.datetime.now().strftime("%H:%M")
    art = CAMEL.format(v=__version__, clock=now, quote=random.choice(QUOTES))
    return _c(art, "\033[38;5;179m", on)


def cmd_scan(a) -> int:
    on = sys.stdout.isatty() and not a.no_color
    rep = scan(a.path, snake=not a.no_snake)
    print(_banner(on))
    print(f"  scanning · {rep.files} files · {rep.lines:,} lines · {rep.root}\n")
    width = max((len(p) for p in rep.per_file), default=10)
    for path, n in sorted(rep.per_file.items(), key=lambda kv: (-kv[1], kv[0]))[: a.top]:
        kinds = {f.label for f in rep.findings if f.path == path}
        badge = "clean ✓" if n == 0 else ", ".join(sorted(kinds))
        color = "\033[32m" if n == 0 else LABEL_COLOR.get(sorted(kinds)[0], "")
        print(f"  {path.ljust(width)}  {_c(badge, color, on)}")
    issues, typos, snakes = rep.issues, rep.by_kind("typo"), rep.by_kind("snake")
    print(f"\n  FILES SCANNED {rep.files}   ISSUES {len(issues)}   TYPOS {len(typos)}   SNAKE_CASE {len(snakes)}")
    return 0


def cmd_spit(a) -> int:
    on = sys.stdout.isatty() and not a.no_color
    rep = scan(a.path, snake=False)
    targets = rep.issues + rep.by_kind("typo")
    if not targets:
        print("no open issues. humpy has nothing to spit on. hmph.")
        return 0
    print(f"◉ {len(targets)} Open   spitting: newest first\n")
    for f in targets:
        label = _c(f.label, LABEL_COLOR.get(f.label, ""), on)
        print(f"  💦 {f.path}:{f.line}  [{label}]  {f.text[:90]}")
    return 0


def cmd_camel(a) -> int:
    fn = {"camel": to_camel, "pascal": to_pascal, "snake": to_snake}[a.style]
    for name in a.names:
        print(fn(name))
    return 0


def cmd_lint(a) -> int:
    rep = scan(a.path)
    snakes = rep.by_kind("snake")
    for f in snakes:
        print(f"{f.path}:{f.line}: {f.text} -> {to_camel(f.text)}")
    if snakes:
        print(f"\n{len(snakes)} snake_case names found. this is a camel repo.", file=sys.stderr)
    return 1 if snakes and not a.exit_zero else 0


def cmd_graph(a) -> int:
    on = sys.stdout.isatty() and not a.no_color
    since = (dt.datetime.now() - dt.timedelta(hours=24)).isoformat(timespec="seconds")
    try:
        out = subprocess.run(["git", "-C", a.path, "log", f"--since={since}", "--format=%ct"],
                             capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        print("not a git repo (or git is missing). the desert is empty.")
        return 1
    now = dt.datetime.now().timestamp()
    buckets = [0] * 24 * 4  # 15-minute cells over the last night
    for ts in out:
        idx = int((now - int(ts)) // 900)
        if 0 <= idx < len(buckets):
            buckets[len(buckets) - 1 - idx] += 1
    top = max(buckets) or 1
    print(f"\n  {len(out)} contributions in the last night\n")
    for row in range(4):
        line = "  "
        for col in range(24):
            n = buckets[col * 4 + row]
            lvl = 0 if n == 0 else 1 + min(3, int(3 * n / top))
            cell = "■ "
            line += _c(cell, GREEN[lvl], on) if on else ("· " if lvl == 0 else "■ ")
        print(line)
    print("\n  Longest streak: all night · 0 water breaks\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="humpy", description="the night-shift camel for your repo")
    p.add_argument("--version", action="version", version=f"humpy {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="walk the repo and report what humpy found")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--top", type=int, default=25, help="how many files to list")
    s.add_argument("--no-snake", action="store_true", help="skip snake_case detection")
    s.add_argument("--no-color", action="store_true")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("spit", help="list every TODO/FIXME/BUG/HACK and typo")  # humpy: ignore
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--no-color", action="store_true")
    s.set_defaults(fn=cmd_spit)

    s = sub.add_parser("camel", help="convert names: snake_case -> camelCase")
    s.add_argument("names", nargs="+")
    s.add_argument("--style", choices=["camel", "pascal", "snake"], default="camel")
    s.set_defaults(fn=cmd_camel)

    s = sub.add_parser("lint", help="flag snake_case names in Python files")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--exit-zero", action="store_true")
    s.set_defaults(fn=cmd_lint)

    s = sub.add_parser("graph", help="contribution graph of the last 24h of git commits")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--no-color", action="store_true")
    s.set_defaults(fn=cmd_graph)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
