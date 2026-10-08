"""The trek. humpy walks the whole repo and notices what humans left in the sand."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .case import find_snake_names, to_camel

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", "target", "vendor",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".next", ".idea", ".tox",
}
PROSE = {".md", ".rst", ".txt", ".adoc"}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "uv.lock"}
HEAVY = 1_000_000          # bytes; anything heavier stays in the oasis
IGNORE = "humpy: " + "ignore"

WORDS = ("TO" + "DO", "FIX" + "ME", "HA" + "CK", "X" + "XX", "B" + "UG")
# Only comments count. Strings and docs mentioning the words leave him calm.
MARKER = re.compile(r"(?:^|\s)(?:#|//|/\*|\*|<!--|--|;)\s*.*?\b(" + "|".join(WORDS) + r")\b(?:\([^)]*\))?[:\s]*(.*)")

KEYS = [
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
]

BASICS = ("README", "LICENSE", ".gitignore", "tests", "CI")


@dataclass
class Marker:
    path: str
    line: int
    kind: str
    text: str


@dataclass
class Key:
    path: str
    line: int
    kind: str
    masked: str


@dataclass
class Snake:
    path: str
    line: int
    name: str
    camel: str


@dataclass
class Report:
    root: str
    files: int = 0
    lines: int = 0
    languages: dict = field(default_factory=dict)
    markers: list = field(default_factory=list)
    keys: list = field(default_factory=list)
    snakes: list = field(default_factory=list)
    heavy: list = field(default_factory=list)
    basics: dict = field(default_factory=dict)

    @property
    def missing(self) -> list:
        return [name for name in BASICS if not self.basics.get(name)]

    @property
    def score(self) -> int:
        points = 100
        points -= 8 * len(self.missing)
        points -= min(30, 2 * len(self.markers))
        points -= min(40, 20 * len(self.keys))
        points -= min(10, 5 * len(self.heavy))
        points -= min(6, len(self.snakes) // 5)
        return max(0, points)

    @property
    def verdict(self) -> str:
        if self.keys:
            return "bad camel (somebody dropped keys in the sand)"
        if self.score >= 90:
            return "good camel"
        if self.score >= 70:
            return "needs water"
        if self.score >= 40:
            return "spat on the carpet"
        return "bad camel"

    def to_dict(self) -> dict:
        return {
            "root": self.root, "score": self.score, "verdict": self.verdict,
            "files": self.files, "lines": self.lines, "languages": self.languages, "missing": self.missing,
            "markers": [vars(m) for m in self.markers], "keys": [vars(k) for k in self.keys],
            "snakes": [vars(s) for s in self.snakes], "heavy": self.heavy,
        }


def mask(value: str) -> str:
    """A camel never repeats a secret. He shows just enough to find it."""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * 8 + value[-2:]


def _looks_like_test(name: str) -> bool:
    low = name.lower()
    return low.startswith("test_") or low.endswith(("_test.py", "_test.go")) or ".test." in low or ".spec." in low


def trek(root: str | os.PathLike = ".", snakes: bool = True) -> Report:
    """Walk `root` and return everything worth a grunt."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(f"{root} is not a directory. camels cross deserts, not single files")
    report = Report(root=str(base))
    basics = dict.fromkeys(BASICS, False)

    for folder, dirs, names in os.walk(base):
        rel_dir = Path(folder).relative_to(base)
        if rel_dir.parts[:2] == (".github", "workflows") and any(n.endswith((".yml", ".yaml")) for n in names):
            basics["CI"] = True
        if rel_dir.name.lower() in {"tests", "test", "__tests__", "spec"}:
            basics["tests"] = True
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)

        for name in sorted(names):
            path = Path(folder) / name
            rel = (rel_dir / name).as_posix()
            if rel_dir == Path("."):
                upper = name.upper()
                basics["README"] |= upper.startswith("README")
                basics["LICENSE"] |= upper.startswith(("LICENSE", "LICENCE", "COPYING"))
                basics[".gitignore"] |= name == ".gitignore"
            basics["tests"] |= _looks_like_test(name)
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > HEAVY:
                report.heavy.append({"path": rel, "bytes": size})
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if b"\0" in raw[:2048]:
                continue  # binary: sand, not text
            report.files += 1
            suffix = path.suffix.lower() or name
            report.languages[suffix] = report.languages.get(suffix, 0) + 1
            text = raw.decode("utf-8", errors="replace")
            look_for_markers = suffix not in PROSE and name not in LOCKFILES
            for number, line in enumerate(text.splitlines(), start=1):
                report.lines += 1
                if len(line) > 2000 or IGNORE in line:
                    continue
                if look_for_markers:
                    found = MARKER.search(line)
                    if found:
                        report.markers.append(Marker(rel, number, found.group(1), found.group(2).strip()[:90]))
                for kind, pattern in KEYS:
                    hit = pattern.search(line)
                    if hit:
                        report.keys.append(Key(rel, number, kind, mask(hit.group(0))))
            if snakes and suffix == ".py":
                lines = text.splitlines()
                for number, snake in find_snake_names(text):
                    if IGNORE not in lines[number - 1]:
                        report.snakes.append(Snake(rel, number, snake, to_camel(snake)))

    report.basics = basics
    report.languages = dict(sorted(report.languages.items(), key=lambda kv: (-kv[1], kv[0]))[:6])
    return report
