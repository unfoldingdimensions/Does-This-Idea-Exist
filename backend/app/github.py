"""GitHub REST API client — repo metadata for the seed-by-GitHub-link feature."""
from urllib.parse import quote, urlparse

import httpx

from . import config, netguard

UA = {"User-Agent": "IdeaExists/0.1 (local startup directory)"}


def parse_repo_url(url: str) -> tuple[str, str]:
    """Accept 'https://github.com/owner/repo', bare 'owner/repo', trailing .git / subpaths."""
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    parsed = urlparse(u)
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {url}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Not a repo URL: {url}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return owner, repo


def fetch_repo(repo_url: str) -> dict:
    """Fetch repo metadata from the GitHub API. Raises ValueError (bad repo) or RuntimeError."""
    owner, repo = parse_repo_url(repo_url)
    headers = dict(UA)
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    # Path segments are percent-encoded so a crafted `owner` cannot smuggle
    # path traversal or a query string into the fixed-host API URL; the target
    # gets the same SSRF pre-check every other outbound call gets.
    url = f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
    try:
        netguard.check_target(url)
    except netguard.BlockedAddressError as exc:
        # A refused target is a network-class failure, NOT a missing repo:
        # raising ValueError here would make verify.py count it as a genuine
        # 404 strike toward the 3-strike dead-flip. RuntimeError is the
        # skip-class signal in both callers (verify skips, seed 502s).
        raise RuntimeError(f"GitHub API target refused: {exc}") from exc
    # follow_redirects: GitHub API returns 301 for renamed/transferred repos
    r = httpx.get(
        url,
        headers=headers,
        timeout=30,
        follow_redirects=True,
    )
    if r.status_code == 404:
        raise ValueError(f"GitHub repo not found: {owner}/{repo}")
    if r.status_code in (403, 429):
        raise RuntimeError(f"GitHub API rate limited (HTTP {r.status_code})")
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API HTTP {r.status_code}: {r.text[:200]}")
    d = r.json()
    return {
        "full_name": d.get("full_name"),
        "name": d.get("name"),
        "description": d.get("description") or "",
        "created_at": (d.get("created_at") or "")[:10],  # YYYY-MM-DD → founded
        "stars": d.get("stargazers_count") or 0,
        "language": d.get("language"),
        "topics": d.get("topics") or [],
        "homepage": d.get("homepage") or "",
        "archived": bool(d.get("archived")),
        "html_url": d.get("html_url") or f"https://github.com/{owner}/{repo}",
    }
