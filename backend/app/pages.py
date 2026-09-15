"""The page plan — the pages a teardown needs, fetched through the app's guard.

`website.fetch_homepage` fetches exactly ONE page. A teardown needs the pages
that ENUMERATE: a pricing page that lists every tier is what pricing (F-07), the
free-tier flag (F-07) and the "no self-host tier" observation (F-09) are built
from; a docs index is what "the docs list no API section" is built from. So the
plan is homepage -> /pricing -> /docs.

Every fetch goes through `netguard.safe_get` — the same UA constant, the same
2 MB cap, one shared timeout. This module adds no second way out to the network.

Three states, kept distinct on purpose:

    readable     we got text back; the page may be evidence
    unreadable   404 / 403 / 429 / 5xx / an empty client-rendered shell —
                 we could not read it
    not_fetched  we had no URL to try

"unreadable" is NEVER collapsed into "this page does not exist". That collapse
is the single easiest way to fake a negative: a page we could not read is
"we could not read it" with low confidence, never "they don't have it"
(docs/teardown-spec.md §8.2). Callers get the state explicitly so they cannot
mistake one for the other.
"""
import logging
import re
import time
from urllib.parse import urljoin, urlparse

from . import netguard, website as ws

log = logging.getLogger("ideasexist")

ROLE_HOME = "homepage"
ROLE_PRICING = "pricing"
ROLE_DOCS = "docs"

# The planned enumerating pages, in fetch order after the homepage. Kept as a
# tuple (not a set) so the fetch order — and therefore the LLM brief — is stable.
PLAN: tuple[tuple[str, str], ...] = (
    (ROLE_PRICING, "/pricing"),
    (ROLE_DOCS, "/docs"),
)

STATE_READABLE = "readable"
STATE_UNREADABLE = "unreadable"
STATE_NOT_FETCHED = "not_fetched"

# Below this many characters of extracted text the page is an empty shell
# (a client-side render returning a skeleton): "we could not read it".
MIN_READABLE_CHARS = 40

UA = ws.UA_BROWSER  # one UA constant for every outbound fetch


def now() -> str:
    """Capture stamps sit beside SQLite's own datetime('now') format."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def join_url(base_url: str, path: str) -> str:
    """Absolute URL for a planned path, honouring the homepage's final host."""
    base = (base_url or "").strip()
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else base
    return urljoin(root + "/", path.lstrip("/"))


_ANCHOR = re.compile(r"""<a\b[^>]*?href\s*=\s*["']([^"']+)["']""", re.I)


def extract_links(html: str, base_url: str, limit: int = 200) -> list[str]:
    """Absolute http(s) hrefs on a page, de-duplicated and order-preserving.

    This is the footer/store-link probe (F-09): a footer that lists every store
    link either lists one or does not, which makes it an enumerating surface for
    "is there a mobile app" — unlike a guessed /mobile URL, which proves nothing.
    """
    out: list[str] = []
    seen: set[str] = set()
    for href in _ANCHOR.findall(html or ""):
        href = href.strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:", "data:")):
            continue
        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        key = absolute.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(absolute)
        if len(out) >= limit:
            break
    return out


def _classify(status: int | None, text: str, error: str = "") -> tuple[str, str]:
    """(state, reason) — the read/unreadable decision, in one place."""
    if error:
        return STATE_UNREADABLE, error[:120]
    if status is None:
        return STATE_UNREADABLE, "no response"
    if status in (401, 403, 429):
        return STATE_UNREADABLE, f"HTTP {status} (refused — bot wall / rate limit)"
    if status >= 400:
        return STATE_UNREADABLE, f"HTTP {status}"
    if len(text or "") < MIN_READABLE_CHARS:
        return STATE_UNREADABLE, "empty shell — no readable text"
    return STATE_READABLE, ""


def fetch_one(url: str, role: str, *, fetcher=None, timeout: float = 25.0) -> dict:
    """Fetch one planned page and return its record. Never raises.

    A network failure is a state, not an exception: a teardown that dies because
    /pricing 404s is a teardown that never runs, and "we could not read /pricing"
    is a perfectly good, useful answer.
    """
    fetch = fetcher or netguard.safe_get
    record = {
        "role": role,
        "url": url,
        "final_url": url,
        "http_status": None,
        "fetched_at": now(),
        "state": STATE_NOT_FETCHED,
        "reason": "",
        "title": "",
        "text": "",
        "links": [],
    }
    try:
        r = fetch(url, headers=UA, timeout=timeout)
        status = getattr(r, "status_code", None)
        body = getattr(r, "text", "") or ""
        content_type = (getattr(r, "headers", {}) or {}).get("content-type", "")
        is_html = "text/html" in content_type.lower() or "<html" in body[:2000].lower()
        text = ws.extract_text(body) if is_html else ""
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        final_url = str(getattr(r, "url", url))
        state, reason = _classify(status, text)
        record.update(
            {
                "final_url": final_url,
                "http_status": status,
                "state": state,
                "reason": reason,
                "title": title,
                "text": text,
                "links": extract_links(body, final_url) if is_html else [],
            }
        )
    except Exception as exc:  # noqa: BLE001 — every failure becomes an explicit state
        log.info("page plan: could not read %s (%s): %s", url, role, exc)
        record["state"], record["reason"] = STATE_UNREADABLE, str(exc)
    return record


def fetch_pages(base_url: str, *, fetcher=None, timeout: float = 25.0) -> dict[str, dict]:
    """The homepage plus every planned enumerating page, each with its state.

    Returns {role: record}. A missing base URL yields three `not_fetched`
    records rather than an empty dict, so a caller can always tell "there was no
    page to try" from "we tried and could not read it".
    """
    records: dict[str, dict] = {}
    base = (base_url or "").strip()
    if not base:
        for role in (ROLE_HOME, *(r for r, _ in PLAN)):
            records[role] = fetch_one("", role, fetcher=fetcher, timeout=timeout)
        for record in records.values():
            record["state"] = STATE_NOT_FETCHED
            record["reason"] = "no website_url to fetch"
        return records
    home = fetch_one(base, ROLE_HOME, fetcher=fetcher, timeout=timeout)
    records[ROLE_HOME] = home
    for role, path in PLAN:
        records[role] = fetch_one(
            join_url(home["final_url"] or base, path), role, fetcher=fetcher, timeout=timeout
        )
    return records


def readable(pages: dict[str, dict]) -> dict[str, dict]:
    """Only the pages we could actually read (the ones that may be evidence)."""
    return {role: rec for role, rec in (pages or {}).items() if rec.get("state") == STATE_READABLE}


def unreadable(pages: dict[str, dict]) -> dict[str, dict]:
    return {role: rec for role, rec in (pages or {}).items() if rec.get("state") == STATE_UNREADABLE}


def enumerating(pages: dict[str, dict]) -> dict[str, dict]:
    """Readable pages that enumerate a whole set — the only pages a negative may
    be built from (F-09). The homepage is not one of them."""
    return {
        role: rec
        for role, rec in readable(pages).items()
        if role in (ROLE_PRICING, ROLE_DOCS)
    }


def urls(pages: dict[str, dict]) -> list[str]:
    """Every fetched URL, for the LLM brief's `observed_on` whitelist."""
    return [rec["url"] for rec in (pages or {}).values() if rec.get("url")]


def brief(pages: dict[str, dict], *, per_page: int = 6000, total: int = 14000) -> str:
    """The already-fetched text handed to the LLM — nothing else may be fetched.

    Unreadable pages are listed by URL with their reason, so the model can say
    "unknown" for them instead of quietly treating an unread page as absence.
    """
    parts: list[str] = []
    used = 0
    for role in (ROLE_HOME, ROLE_PRICING, ROLE_DOCS):
        rec = (pages or {}).get(role)
        if not rec:
            continue
        header = f"--- {role}: {rec['url']} [{rec['state']}]"
        if rec["state"] != STATE_READABLE:
            parts.append(f"{header} — {rec['reason'] or 'could not read this page'}")
            continue
        chunk = rec["text"][:per_page]
        used += len(chunk)
        if used > total:
            chunk = chunk[: max(0, len(chunk) - (used - total))]
        parts.append(f"{header}\n{chunk}")
    return "\n\n".join(parts)
