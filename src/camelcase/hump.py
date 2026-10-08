"""hump.py — the file from the video. Yes, it runs (give it any repo/issue objects)."""
from __future__ import annotations

from .oasis import retry


@retry(on=429, tries=7)  # no water needed
async def cross(repo, issue):
    page = await repo.trek(issue.url)
    bug = page.find("stack trace")
    patch = await bug.chew(twice=True)
    await repo.commit(patch, "fix: retry on 429")
    return "good camel"  # obviously
