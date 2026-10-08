"""oasis — retry helpers for the long walk between requests.

    @retry(on=429, tries=7)  # no water needed
    async def cross(repo, issue): ...

Works with sync and async callables. An attempt is retried when it raises an
exception whose ``status_code`` (or ``response.status_code``) is in ``on``,
or when it returns an object with such a ``status_code``.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import random
import time
from typing import Any, Callable, Iterable

__all__ = ["retry", "GaveUp"]


class GaveUp(RuntimeError):
    """Raised when every try came back thirsty."""

    def __init__(self, tries: int, last: Any):
        super().__init__(f"gave up after {tries} tries (last: {last!r})")
        self.tries = tries
        self.last = last


def _status(obj: Any) -> int | None:
    code = getattr(obj, "status_code", None)
    if code is None:
        resp = getattr(obj, "response", None)
        code = getattr(resp, "status_code", None)
    return code if isinstance(code, int) else None


def _delay(attempt: int, base: float, cap: float) -> float:
    # exponential backoff with full jitter, like a camel deciding when to stand up
    return random.uniform(0, min(cap, base * (2 ** attempt)))


def retry(on: int | Iterable[int] = 429, tries: int = 7, base: float = 0.5, cap: float = 30.0,
          sleep: Callable[[float], Any] | None = None):
    """Retry a call while it keeps hitting the given HTTP status codes."""
    codes = {on} if isinstance(on, int) else set(on)
    if tries < 1:
        raise ValueError("tries must be >= 1")

    def deco(fn):
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrapper(*a, **kw):
                last: Any = None
                for attempt in range(tries):
                    try:
                        out = await fn(*a, **kw)
                    except Exception as exc:  # noqa: BLE001
                        if _status(exc) not in codes:
                            raise
                        last = exc
                    else:
                        if _status(out) not in codes:
                            return out
                        last = out
                    if attempt < tries - 1:
                        d = _delay(attempt, base, cap)
                        await (sleep(d) if sleep else asyncio.sleep(d))
                raise GaveUp(tries, last)
            return awrapper

        @functools.wraps(fn)
        def wrapper(*a, **kw):
            last: Any = None
            for attempt in range(tries):
                try:
                    out = fn(*a, **kw)
                except Exception as exc:  # noqa: BLE001
                    if _status(exc) not in codes:
                        raise
                    last = exc
                else:
                    if _status(out) not in codes:
                        return out
                    last = out
                if attempt < tries - 1:
                    (sleep or time.sleep)(_delay(attempt, base, cap))
            raise GaveUp(tries, last)
        return wrapper

    return deco
