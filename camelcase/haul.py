"""The haul. humpy carries back the open issues of a GitHub repository, on his humps."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .oasis import retry

API = "https://api.github.com"
WORTH_CARRYING = ("good first issue", "help wanted", "bug")


class _Thirsty(Exception):
    """A 429 or 403 from GitHub. Retried by the oasis, then reported."""

    def __init__(self, code: int):
        super().__init__(code)
        self.status_code = code


@retry(on=(429,), tries=3, base=1.0)
def _get(url: str, token: str | None):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "camelcase-humpy",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            raise _Thirsty(error.code) from error
        raise


def haul(repo: str, limit: int = 100, token: str | None = None, now: datetime | None = None) -> dict:
    """Return the open issues of `owner/name`, oldest first, pull requests left behind."""
    if repo.count("/") != 1:
        raise ValueError("he needs an address like owner/name")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    now = now or datetime.now(timezone.utc)
    issues, page = [], 1
    while len(issues) < limit and page <= 10:
        url = f"{API}/repos/{repo}/issues?state=open&sort=created&direction=asc&per_page=100&page={page}"
        try:
            batch = _get(url, token)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise LookupError(f"{repo}: no such repository, or the gate is closed to him") from error
            raise
        except Exception as error:  # GaveUp or _Thirsty
            if getattr(error, "status_code", None) in (403, 429) or type(error).__name__ == "GaveUp":
                raise PermissionError("GitHub says slow down. Set GITHUB_TOKEN for a bigger water ration") from error
            raise
        if not batch:
            break
        for item in batch:
            if "pull_request" in item:
                continue
            created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "age_days": (now - created).days,
                "labels": [label["name"] for label in item.get("labels", [])],
                "assigned": bool(item.get("assignees")),
                "comments": item.get("comments", 0),
                "url": item["html_url"],
            })
        page += 1
    issues = issues[:limit]
    labels: dict = {}
    for issue in issues:
        for label in issue["labels"]:
            labels[label] = labels.get(label, 0) + 1
    cargo = [i for i in issues if not i["assigned"] and any(lb.lower() in WORTH_CARRYING for lb in i["labels"])]
    return {
        "repo": repo,
        "open": len(issues),
        "oldest": issues[:5],
        "labels": dict(sorted(labels.items(), key=lambda kv: (-kv[1], kv[0]))[:6]),
        "cargo": cargo[:8],
    }
