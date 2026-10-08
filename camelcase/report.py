"""How humpy tells you what he found: in the terminal, or as Markdown for a job summary."""

from __future__ import annotations

from pathlib import Path

from .trek import BASICS, Report

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN = (f"\033[{n}m" for n in (31, 32, 33, 34, 35, 36))
SAND = "\033[38;5;179m"


class Paint:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, text: str, *codes: str) -> str:
        return f"{''.join(codes)}{text}{RESET}" if self.enabled else text


def bar(score: int, width: int = 24) -> str:
    filled = round(width * score / 100)
    return "#" * filled + "-" * (width - filled)


def terminal(report: Report, color: bool = True, limit: int = 12) -> str:
    p = Paint(color)
    tone = GREEN if report.score >= 90 else YELLOW if report.score >= 70 else RED
    out = [
        p("humpy", BOLD, SAND) + p(" trekked ", DIM) + p(Path(report.root).name or report.root, BOLD),
        p(f"  {report.files} files, {report.lines:,} lines", DIM)
        + p("   " + "  ".join(f"{ext} {n}" for ext, n in report.languages.items()), DIM),
        "",
        p("  basics", BOLD),
    ]
    for name in BASICS:
        ok = report.basics.get(name)
        out.append("    " + (p("ok     ", GREEN) if ok else p("missing", RED)) + f"  {name}")
    out += ["", p(f"  things buried in the sand: {len(report.markers)}", BOLD)]
    for m in report.markers[:limit]:
        out.append(f"    {p(m.kind.ljust(5), YELLOW)} {p(f'{m.path}:{m.line}', BLUE)}  {m.text}")
    if len(report.markers) > limit:
        out.append(p(f"    ... and {len(report.markers) - limit} more", DIM))
    out += ["", p(f"  keys dropped in the sand: {len(report.keys)}", BOLD)]
    for k in report.keys[:limit]:
        out.append(f"    {p(k.kind, RED)} {p(f'{k.path}:{k.line}', BLUE)}  {k.masked}")
    if report.snakes:
        out += ["", p(f"  snakes in the desert: {len(report.snakes)}", BOLD)]
        for s in report.snakes[:5]:
            out.append(f"    {p(f'{s.path}:{s.line}', BLUE)}  {s.name} {p('->', DIM)} {p(s.camel, CYAN)}")
        if len(report.snakes) > 5:
            out.append(p(f"    ... and {len(report.snakes) - 5} more (humpy camel --help)", DIM))
    if report.heavy:
        out += ["", p(f"  too heavy to carry: {len(report.heavy)}", BOLD)]
        for big in report.heavy[:5]:
            out.append(f"    {big['path']}  {big['bytes'] / 1_000_000:.1f} MB")
    out += [
        "",
        "  " + p(f"good camel score  {report.score}/100  ", BOLD) + p(bar(report.score), tone),
        "  " + p(f"verdict: {report.verdict}", tone, BOLD),
    ]
    return "\n".join(out)


def markdown(report: Report, limit: int = 30) -> str:
    lines = [
        "## 🐫 camelcase night shift report",
        "",
        f"**Good camel score: {report.score}/100** ({report.verdict})",
        "",
        f"Trekked {report.files} files and {report.lines:,} lines.",
        "",
        "| Basics | Found |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {'yes' if report.basics.get(name) else '**missing**'} |" for name in BASICS]
    lines += ["", f"### Buried in the sand ({len(report.markers)})", ""]
    if report.markers:
        lines += ["| Kind | Where | Note |", "| --- | --- | --- |"]
        for m in report.markers[:limit]:
            lines.append(f"| {m.kind} | `{m.path}:{m.line}` | {m.text.replace('|', chr(92) + '|') or ' '} |")
        if len(report.markers) > limit:
            lines.append(f"| | | and {len(report.markers) - limit} more |")
    else:
        lines.append("Nothing buried here.")
    lines += ["", f"### Keys dropped in the sand ({len(report.keys)})", ""]
    if report.keys:
        lines += ["| Kind | Where | Looks like |", "| --- | --- | --- |"]
        lines += [f"| {k.kind} | `{k.path}:{k.line}` | `{k.masked}` |" for k in report.keys[:limit]]
        lines += ["", "Rotate these now. Deleting the line does not remove it from git history."]
    else:
        lines.append("None. He spat twice to be sure.")
    if report.snakes:
        lines += ["", f"### Snakes in the desert ({len(report.snakes)})", ""]
        lines += [f"- `{s.path}:{s.line}` `{s.name}` → `{s.camel}`" for s in report.snakes[:10]]
    if report.heavy:
        lines += ["", f"### Too heavy to carry ({len(report.heavy)})", ""]
        lines += [f"- `{big['path']}` ({big['bytes'] / 1_000_000:.1f} MB)" for big in report.heavy[:10]]
    return "\n".join(lines) + "\n"


def haul_terminal(result: dict, color: bool = True) -> str:
    p = Paint(color)
    out = [
        p("humpy", BOLD, SAND) + p(" hauled ", DIM) + p(result["repo"], BOLD),
        p(f"  {result['open']} open issues", DIM),
    ]
    if result["labels"]:
        out.append(p("  " + "  ".join(f"{name} {count}" for name, count in result["labels"].items()), DIM))
    out += ["", p("  oldest tracks in the sand", BOLD)]
    for issue in result["oldest"]:
        age = (str(issue["age_days"]) + "d").rjust(6)
        out.append(f"    {p('#' + str(issue['number']), BLUE)}  {p(age, YELLOW)}  {issue['title'][:70]}")
    out += ["", p(f"  worth carrying: {len(result['cargo'])}", BOLD)]
    for issue in result["cargo"]:
        out.append(f"    {p('#' + str(issue['number']), BLUE)}  {issue['title'][:56]}  {p(', '.join(issue['labels'][:3]), MAGENTA)}")
    if not result["cargo"]:
        out.append(p("    nothing labelled bug, help wanted or good first issue without an owner", DIM))
    return "\n".join(out)
