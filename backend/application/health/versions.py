"""MISP version parsing and latest-release lookup, shared by the health rules and the Up-To-Date plugin"""

import re
from typing import Optional, Tuple

import requests

from application import redisModel

GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/MISP/MISP/releases/latest"
KEY_LATEST_RELEASE = "health-latest-release"
LATEST_RELEASE_TTL = 60 * 60
# A failed lookup is remembered for a while, so that an instance without internet access does not wait on GitHub
# every time health is evaluated
LATEST_RELEASE_FAILURE_TTL = 10 * 60
GITHUB_TIMEOUT = 5

VERSION_RE = re.compile(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?")

Version = Tuple[int, int, int]


def parse_version(text) -> Optional[Version]:
    """`v2.5.1`, `2.5.1`, `2.5`, `3.0.0-rc1` or `2.5.1 (abcdef)` → (major, minor, patch); anything else → None"""
    if not isinstance(text, str):
        return None
    match = VERSION_RE.match(text)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def format_version(version: Optional[Version]) -> str:
    return "?" if version is None else ".".join(str(part) for part in version)


def how_far_behind(current: Optional[Version], latest: Optional[Version]) -> Optional[str]:
    """`None` when up to date, newer than the latest release, or when either version is unknown; otherwise the most
    significant part that differs: `major`, `minor` or `patch`. Versions are ordered, not compared for equality: a
    server running a newer branch than GitHub's "latest" release (e.g. 3.0 while latest is 2.5) is not outdated"""
    if current is None or latest is None or current >= latest:
        return None
    if current[0] != latest[0]:
        return "major"
    if current[1] != latest[1]:
        return "minor"
    return "patch"


def fetch_latest_release() -> Optional[str]:
    try:
        response = requests.get(GITHUB_LATEST_RELEASE_URL, timeout=GITHUB_TIMEOUT,
                                headers={"Accept": "application/vnd.github+json"})
        if response.status_code != 200:
            return None
        tag = response.json().get("tag_name")
        return tag if parse_version(tag) is not None else None
    except (requests.RequestException, ValueError, AttributeError):
        return None


def latest_release() -> Optional[str]:
    """Tag of the latest MISP release on GitHub (e.g. `v2.5.1`), cached in Redis for an hour. None when unknown"""
    try:
        cached = redisModel.redisClient.get(KEY_LATEST_RELEASE)
    except Exception:
        cached = None
    if cached is not None:
        return cached or None
    tag = fetch_latest_release()
    try:
        redisModel.redisClient.set(KEY_LATEST_RELEASE, tag or "",
                                   ex=LATEST_RELEASE_TTL if tag else LATEST_RELEASE_FAILURE_TTL)
    except Exception:
        pass
    return tag
