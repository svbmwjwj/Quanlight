"""Network access: plain downloads, upstream commit ids and the v2fly data tarball."""

import io
import json
import os
import tarfile
import time
import urllib.request
from pathlib import Path

USER_AGENT = "quanlight-build"


class FetchError(Exception):
    pass


def _request(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_bytes(url: str, retries: int = 3, headers: dict[str, str] | None = None) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return _request(url, headers)
        except OSError as exc:  # URLError and HTTPError are OSError subclasses
            last = exc
            time.sleep(2**attempt)
    raise FetchError(f"failed to fetch {url}: {last}")


def fetch_text(url: str, retries: int = 3) -> str:
    return fetch_bytes(url, retries).decode("utf-8")


def fetch_commit(repo: str, branch: str) -> str:
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    data = json.loads(fetch_bytes(f"https://api.github.com/repos/{repo}/commits/{branch}", headers=headers))
    return data["sha"]


def fetch_v2fly_data(dest: Path, url: str) -> Path:
    """Download and unpack the v2fly repository; return its data/ directory."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(fetch_bytes(url)), mode="r:gz") as tar:
        tar.extractall(dest, filter="data")
    matches = sorted(dest.glob("*/data"))
    if not matches:
        raise FetchError("v2fly archive has no data/ directory")
    return matches[0]
