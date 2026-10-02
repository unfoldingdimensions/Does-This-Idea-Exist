"""Sourcing channels — where candidates come from, with their provenance attached.

Phase C, task 2. Each adapter turns one public source into candidate dicts shaped
for `candidates.stage()`:

    {"url": ..., "name": ..., "source_url": ..., "github_url": ..., "meta_json": ...}

Design rules, each with a reason:

* **Injected client, injected sleep.** Every adapter takes its HTTP client and its
  sleep function as arguments, so the tests run on fixtures with no network and no
  waiting, and the real run is a separate, explicit act. A test that needs the
  internet is a test that fails for reasons that are not the code's.
* **Only documented surfaces.** The four channels read raw.githubusercontent.com
  (static files), api.github.com (the GitHub API, token-aware), hn.algolia.com
  (HN's public API) and two local JSON files. Nothing here scrapes a bot-walled
  product page — that is a different job with different rules, and it is
  deliberately not in this phase.
* **Provenance is mandatory and specific.** `source_url` is the exact page, API
  row or file the candidate came from — not the channel name. The staging store
  refuses a candidate without it, so an adapter that forgot would fail loudly at
  the first write instead of quietly filling the store with unattributable rows.
* **Lazy, paged, throttled.** Adapters are generators: the caller decides when to
  stop (the CLI's `--limit`), and pacing happens between requests, not after the
  last one.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from . import config

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_FILES = {
    "famous": REPO_ROOT / "backend" / "data" / "seed_famous.json",
    "design_library": REPO_ROOT / "backend" / "data" / "seed_design_library.json",
}

# A candidate is a plain dict; the store validates it. This alias is for readers.
Candidate = dict

_SLEEP: Callable[[float], None] = time.sleep
UA = "IdeaExists-Sourcing/1.0 (+https://github.com/unfoldingdimensions/Does-This-Idea-Exist)"

# Links that are never a product: badges, licences, contribution guides, socials
# and the list's own scaffolding. Filtering here keeps the staging store readable;
# the alternative is a reviewer scrolling past shields.io forty times.
_NOISE = re.compile(
    r"(shields\.io|badgen\.net|badge\.fury|awesome\.re|/blob/|/tree/|/issues|/pulls"
    r"|/contribute|/contributing|/license|/code_of_conduct|/security"
    r"|twitter\.com|/x\.com/|facebook\.com|linkedin\.com|reddit\.com|youtube\.com"
    r"|patreon\.com|opencollective\.com|github\.sponsors|buymeacoffee"
    r"|^mailto:|^#|^\.)",
    re.IGNORECASE,
)

_MD_LINK = re.compile(r"\[(?P<text>[^\]\n]{1,120})\]\((?P<url>https?://[^)\s]+)\)")
_MD_HTML_LINK = re.compile(r"<a[^>]+href=[\"'](?P<url>https?://[^\"'>\s]+)[\"'][^>]*>(?P<text>[^<]{0,120})</a>",
                           re.IGNORECASE)


def _throttle(sleep: Callable[[float], None], seconds: float) -> None:
    """Pace requests between calls. Politeness is a parameter, not a constant."""
    if seconds and seconds > 0:
        sleep(seconds)


def _clean_name(text: str | None) -> str | None:
    if not text:
        return None
    name = re.sub(r"\s+", " ", text.replace("*", "").replace("`", "")).strip(" -–—:·|")
    return name or None


# --- channel: curated lists (awesome-* and "alternatives to X" indexes) -------

def curated_lists(spec: dict, client: Any, *, sleep: Callable[[float], None] = _SLEEP,
                  throttle_s: float = 1.0, max_pages: int = 1) -> Iterator[Candidate]:
    """Parse a markdown list's links into candidates.

    `spec` = `{"url": <raw markdown url>, "source_url": <the list's own page>,
    "name": <optional label>}`. A malformed body yields NOTHING rather than
    raising: one bad list must not abandon a whole sourcing run.

    `max_pages` is accepted for signature parity with the paging channels (the
    CLI passes one shape to every adapter) and ignored: a list is a single body.
    """
    url = (spec or {}).get("url")
    if not url:
        return
    source_url = (spec or {}).get("source_url") or url
    try:
        response = client.get(url, headers={"User-Agent": UA}, timeout=30)
    except Exception as exc:  # noqa: BLE001 — a fetch failure is data, not a crash
        yield {"_error": f"curated_lists: fetch failed for {url}: {exc}", "_source_url": source_url}
        return
    if getattr(response, "status_code", None) != 200:
        yield {"_error": f"curated_lists: HTTP {getattr(response, 'status_code', '?')} for {url}",
               "_source_url": source_url}
        return
    body = getattr(response, "text", "") or ""
    seen: set[str] = set()
    for match in list(_MD_LINK.finditer(body)) + list(_MD_HTML_LINK.finditer(body)):
        link = match.group("url").rstrip(").,;")
        name = _clean_name(match.groupdict().get("text"))
        if not link.startswith("http") or _NOISE.search(link) or link in seen:
            continue
        seen.add(link)
        yield {"url": link, "name": name, "source_url": source_url}
    _throttle(sleep, throttle_s)


# --- channel: GitHub topics + search ----------------------------------------

def github_topics(spec: dict, client: Any, *, sleep: Callable[[float], None] = _SLEEP,
                  throttle_s: float = 1.0, max_pages: int = 3) -> Iterator[Candidate]:
    """GitHub Search API: repos for a topic/query, best first.

    `spec` = `{"query": "topic:saas stars:>200", "per_page": 100}`. Search is
    capped at 1,000 results by GitHub itself, so `max_pages` is a deliberate
    budget on top of that. A 403 names the token, because unauthenticated search
    is 10 requests/minute and a silent stall is worse than an error.
    """
    query = (spec or {}).get("query") or "topic:saas stars:>500"
    per_page = min(max(int((spec or {}).get("per_page", 100) or 100), 1), 100)
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    for page in range(1, max(1, max_pages) + 1):
        if page > 1:
            _throttle(sleep, throttle_s)
        try:
            response = client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc",
                        "per_page": per_page, "page": page},
                headers=headers, timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            yield {"_error": f"github_topics: fetch failed on page {page}: {exc}",
                   "_source_url": f"https://api.github.com/search/repositories?q={query}"}
            return
        status = getattr(response, "status_code", None)
        if status == 401:
            yield {"_error": "github_topics: HTTP 401 — the stored GITHUB_TOKEN was REJECTED "
                             "(invalid, expired or revoked). Unauthenticated search still works "
                             "but is capped at 10 requests/minute, so a big pull needs a fresh "
                             "token in backend/.env. Nothing was staged for this source.",
                   "_source_url": "https://api.github.com/search/repositories"}
            return
        if status == 403:
            yield {"_error": "github_topics: HTTP 403 (rate limited) — set GITHUB_TOKEN for "
                             "anything beyond a handful of searches",
                   "_source_url": "https://api.github.com/search/repositories"}
            return
        if status != 200:
            yield {"_error": f"github_topics: HTTP {status} on page {page}",
                   "_source_url": "https://api.github.com/search/repositories"}
            return
        try:
            items = (response.json() or {}).get("items") or []
        except Exception:  # noqa: BLE001 — a truncated body yields nothing
            items = []
        if not items:
            return
        for item in items:
            full_name = item.get("full_name")
            html_url = item.get("html_url") or (f"https://github.com/{full_name}" if full_name else None)
            if not html_url:
                continue
            # Prefer the project's own site as the candidate URL (it is what the
            # archive stores as website_url and what dedupe matches on); the repo
            # URL rides along so the GitHub path stays available.
            homepage = (item.get("homepage") or "").strip()
            url = homepage if homepage.startswith("http") else html_url
            yield {
                "url": url,
                "name": item.get("name") or full_name,
                "github_url": html_url,
                "source_url": f"https://api.github.com/search/repositories?q={query}&page={page}",
                "meta_json": json.dumps({
                    "stars": item.get("stargazers_count"),
                    "forks": item.get("forks_count"),
                    "archived": item.get("archived"),
                    "pushed_at": item.get("pushed_at"),
                    "description": (item.get("description") or "")[:400] or None,
                    "topics": item.get("topics") or [],
                }),
            }


# --- channel: HN "Show HN" ---------------------------------------------------

def show_hn(spec: dict, client: Any, *, sleep: Callable[[float], None] = _SLEEP,
            throttle_s: float = 1.0, max_pages: int = 3) -> Iterator[Candidate]:
    """Show HN via HN's own public Algolia API — no key, no scraping.

    `spec` = `{"query": "show_hn", "min_points": 40}`. The HN item URL is the
    provenance (`news.ycombinator.com/item?id=…`), which is what a reviewer needs
    to check a candidate's origin years later.
    """
    query = (spec or {}).get("query") or "show_hn"
    min_points = int((spec or {}).get("min_points", 40) or 0)
    for page in range(0, max(1, max_pages)):
        if page:
            _throttle(sleep, throttle_s)
        params = {"tags": "show_hn", "hitsPerPage": 100, "page": page}
        if query and query != "show_hn":
            params["query"] = query
        if min_points:
            params["numericFilters"] = f"points>{min_points}"
        try:
            response = client.get("https://hn.algolia.com/api/v1/search",
                                  params=params, headers={"User-Agent": UA}, timeout=30)
        except Exception as exc:  # noqa: BLE001
            yield {"_error": f"show_hn: fetch failed on page {page}: {exc}",
                   "_source_url": "https://hn.algolia.com/api/v1/search"}
            return
        if getattr(response, "status_code", None) != 200:
            yield {"_error": f"show_hn: HTTP {getattr(response, 'status_code', '?')} on page {page}",
                   "_source_url": "https://hn.algolia.com/api/v1/search"}
            return
        try:
            hits = (response.json() or {}).get("hits") or []
        except Exception:  # noqa: BLE001
            hits = []
        if not hits:
            return
        for hit in hits:
            url = (hit.get("url") or "").strip()
            object_id = hit.get("objectID")
            if not url.startswith("http") or not object_id:
                # A text-only Show HN has nowhere to point; it is not a candidate.
                continue
            yield {
                "url": url,
                "name": _clean_name(hit.get("title")),
                "source_url": f"https://news.ycombinator.com/item?id={object_id}",
                "meta_json": json.dumps({"points": hit.get("points"), "author": hit.get("author"),
                                         "created_at": hit.get("created_at")}),
            }


# --- channel: the local bundles ---------------------------------------------

def bundles(spec: dict | None = None, client: Any = None, *,
            sleep: Callable[[float], None] = _SLEEP, throttle_s: float = 0.0,
            max_pages: int = 0) -> Iterator[Candidate]:
    """The two seed JSON files, re-expressed as a channel.

    No network, no key, and already-curated rows — the cheapest yield there is.
    Provenance is the FILE (and the row's position in it), because that is
    genuinely where the candidate came from.

    `client`/`sleep`/`throttle_s`/`max_pages` exist for signature parity with the
    network channels and are unused: there is nothing to fetch and nothing to pace.
    """
    wanted: Iterable[str] = (spec or {}).get("bundles") or SEED_FILES.keys()
    for bundle in wanted:
        path = SEED_FILES.get(bundle)
        if path is None or not path.is_file():
            yield {"_error": f"bundles: no such bundle {bundle!r}", "_source_url": str(path)}
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — a broken file yields nothing, loudly
            yield {"_error": f"bundles: {path.name} is not valid JSON: {exc}",
                   "_source_url": str(path)}
            continue
        if not isinstance(rows, list):
            yield {"_error": f"bundles: {path.name} is not a list of rows",
                   "_source_url": str(path)}
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            url = (row.get("website_url") or row.get("github_url") or "").strip()
            if not url.startswith("http"):
                continue
            yield {
                "url": url,
                "name": row.get("name"),
                "github_url": row.get("github_url"),
                "source_url": f"file:{path.as_posix()}#{index}",
            }


CHANNELS: dict[str, Callable[..., Iterator[Candidate]]] = {
    "curated_lists": curated_lists,
    "github_topics": github_topics,
    "show_hn": show_hn,
    "bundles": bundles,
}


def collect(channel: str, spec: dict, client: Any = None, **kwargs: Any) -> Iterator[Candidate]:
    """Dispatch to a channel. Unknown name -> a loud error, not a silent empty run."""
    adapter = CHANNELS.get((channel or "").strip())
    if adapter is None:
        raise ValueError(f"unknown channel {channel!r}: expected one of {sorted(CHANNELS)}")
    return adapter(spec or {}, client, **kwargs)
