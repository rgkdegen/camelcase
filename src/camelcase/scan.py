"""Walk a repo like a camel walks a desert: slowly, and noticing everything."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .case import find_snake_names

__all__ = ["Finding", "Report", "scan"]

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".java", ".kt", ".c", ".h", ".cpp", ".md", ".txt",
            ".toml", ".yml", ".yaml", ".json", ".sh", ".css", ".html"}
MARKERS = re.compile(r"\b(TODO|FIXME|BUG|HACK|XXX)\b[:\s]*(.*)")  # humpy: ignore
TYPOS = {  # humpy: ignore
    "teh": "the", "recieve": "receive", "seperate": "separate", "occured": "occurred", "definately": "definitely",  # humpy: ignore
    "lenght": "length", "retreive": "retrieve", "enviroment": "environment", "dependancy": "dependency",  # humpy: ignore
    "succesful": "successful", "untill": "until", "wierd": "weird", "acheive": "achieve", "adress": "address",  # humpy: ignore
}
IGNORE = "humpy: " + "ignore"
_TYPO_RX = re.compile(r"\b(" + "|".join(TYPOS) + r")\b", re.I)


@dataclass
class Finding:
    kind: str          # todo | fixme | bug | hack | typo | snake
    path: str
    line: int
    text: str

    @property
    def label(self) -> str:
        return {"todo": "todo", "fixme": "bug", "bug": "bug", "hack": "dead code", "xxx": "bug",
                "typo": "typo", "snake": "camelcase"}.get(self.kind, self.kind)


@dataclass
class Report:
    root: str
    files: int = 0
    lines: int = 0
    findings: list[Finding] = field(default_factory=list)
    per_file: dict[str, int] = field(default_factory=dict)

    def by_kind(self, *kinds: str) -> list[Finding]:
        return [f for f in self.findings if f.kind in kinds]

    @property
    def issues(self) -> list[Finding]:
        return self.by_kind("todo", "fixme", "bug", "hack", "xxx")


def _iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.suffix.lower() in TEXT_EXT:
                yield p


def scan(root: str | os.PathLike = ".", snake: bool = True, max_bytes: int = 1_000_000) -> Report:
    root = Path(root).resolve()
    rep = Report(root=str(root))
    for p in _iter_files(root):
        try:
            if p.stat().st_size > max_bytes:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(p.relative_to(root))
        rep.files += 1
        rep.lines += text.count("\n") + 1
        n0 = len(rep.findings)
        for i, line in enumerate(text.splitlines(), 1):
            if IGNORE in line:
                continue
            m = MARKERS.search(line)
            if m:
                rep.findings.append(Finding(m.group(1).lower(), rel, i, m.group(2).strip() or m.group(1)))
            for t in _TYPO_RX.finditer(line):
                rep.findings.append(Finding("typo", rel, i, f"{t.group(1)} -> {TYPOS[t.group(1).lower()]}"))
        if snake and p.suffix == ".py":
            for ln, name in find_snake_names(text):
                rep.findings.append(Finding("snake", rel, ln, name))
        rep.per_file[rel] = len(rep.findings) - n0
    return rep
