"""The actual camel case part."""
from __future__ import annotations

import re

__all__ = ["to_camel", "to_pascal", "to_snake", "find_snake_names"]

_SPLIT = re.compile(r"[\s_\-\.]+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _words(name: str) -> list[str]:
    return [w for w in _SPLIT.split(name.strip()) if w]


def to_camel(name: str) -> str:
    """'stack_trace_url' -> 'stackTraceUrl'. Leading underscores are kept."""
    lead = len(name) - len(name.lstrip("_"))
    words = _words(name)
    if not words:
        return name
    head, *rest = words
    return "_" * lead + head.lower() + "".join(w[:1].upper() + w[1:].lower() for w in rest)


def to_pascal(name: str) -> str:
    """'good camel' -> 'GoodCamel'."""
    return "".join(w[:1].upper() + w[1:].lower() for w in _words(name))


def to_snake(name: str) -> str:
    """'goodCamel' -> 'good_camel'. For when you need to go back to the zoo."""
    return "_".join(w.lower() for w in _words(name))


_DEF = re.compile(r"^\s*(?:async\s+)?def\s+([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*\(", re.M)
_ASSIGN = re.compile(r"^\s*([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*=(?!=)", re.M)


def find_snake_names(source: str) -> list[tuple[int, str]]:
    """Return (line_no, name) for snake_case function and variable names in Python source."""
    hits: dict[tuple[int, str], None] = {}
    for rx in (_DEF, _ASSIGN):
        for m in rx.finditer(source):
            line = source.count("\n", 0, m.start(1)) + 1
            hits[(line, m.group(1))] = None
    return sorted(hits)
