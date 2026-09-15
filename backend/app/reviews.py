"""Reviews — what their users ask for, never a score (F-23, spec §9).

Reviews answer the one question a teardown otherwise cannot: does this thing
actually have users, and what do those users ask for?

The rules, and they are the point of the module:

  * **Fetch and report, never score.** No star aggregate of our own, no NPS, no
    sentiment score. Where a platform shows a rating it is quoted with its
    source, and upvote/score counts are deliberately NOT read at all — nothing
    numeric about a review enters the archive.
  * **Positive and negative are both surfaced**, labelled as the reviewer's view.
  * **Negative reviews become "what their users ask for"**: the features and
    fixes reviewers actually requested, each linked to the review it came from.
    That is gap-table dimension 7's input. The product hands the founder what
    users asked for and stops there — "you should build X" is never printed.
  * **Providers are config, not code** (config.REVIEW_SOURCES), so adding a
    platform is an edit, not a phase.
  * **A walled provider (403/429) is a SKIP**, never a failure or a strike — the
    same tri-state rule verify.py uses, for the same reason (G2/Capterra/
    Trustpilot bot-wall datacenter traffic; a wall is not a dead company).

One evidence row per review, `evidence_type='review'`, `source_url` = the review
permalink, `provenance='machine_drafted'` until a human confirms.
"""
import html as html_lib
import json
import logging
import re
from urllib.parse import quote_plus, urlparse

from . import config, evidence as ev, netguard
from . import pages as pages_mod

log = logging.getLogger("ideasexist")

STATE_FETCHED = "fetched"
STATE_SKIPPED = "skipped"

UA = pages_mod.UA

# Markers, not models: a reviewer's ask is almost always phrased one of these
# ways, and a deterministic pass keeps the whole module testable offline.
ASK_MARKERS = (
    "i wish", "wish it", "wish there", "would love", "would like", "please add",
    "should add", "needs to", "need a", "needs a", "could use", "would pay for",
    "no support for", "doesn't support", "does not support", "why is there no",
    "any plans for", "hope they add", "if only", "missing", "request",
)
POSITIVE_MARKERS = (
    "love", "excellent", "awesome", "great", "best", "amazing", "fantastic",
    "works well", "perfect", "recommend", "brilliant",
)
NEGATIVE_MARKERS = (
    "wish", "missing", "hate", "broken", "crash", "slow", "frustrat", "annoying",
    "cannot", "can't", "no support", "expensive", "limited", "bug", "disappointing",
    "worse", "unusable",
)

MAX_ASKS_PER_REVIEW = 3
ASK_MAX_CHARS = 160
EXCERPT_MAX_CHARS = 600


def _text(value, limit: int | None = None) -> str:
    out = "" if value is None else re.sub(r"\s+", " ", str(value)).strip()
    return out[:limit] if limit else out


def _query_for(startup) -> str:
    """The search term for a competitor: its domain, which is what a reviewer
    would name. Falls back to the display name."""
    url = ""
    try:
        url = startup["website_url"] or ""
    except (KeyError, IndexError, TypeError):
        url = ""
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host:
        return host
    try:
        return _text(startup["name"])
    except (KeyError, IndexError, TypeError):
        return ""


def classify(text: str) -> str:
    """positive | negative | unclassified — the reviewer's view, never a score.

    A request ("I wish it had…") is classified negative on purpose: dimension 7
    is fed by what users ask for, and an ask is an unmet need.
    """
    lowered = (text or "").lower()
    if any(m in lowered for m in ASK_MARKERS) or any(m in lowered for m in NEGATIVE_MARKERS):
        return "negative"
    if any(m in lowered for m in POSITIVE_MARKERS):
        return "positive"
    return "unclassified"


def extract_asks(text: str) -> list[str]:
    """The features/fixes a reviewer asked for, as short clauses.

    Capability-level de-duplication ("offline mode" / "work without internet")
    belongs to the gap table (dimension 7, Phase 3): this returns what the review
    says, and Phase 3 groups it.
    """
    if not text:
        return []
    clauses = re.split(r"(?<=[.!?;])\s+|\n+", _text(text))
    out: list[str] = []
    for clause in clauses:
        lowered = clause.lower()
        if not any(marker in lowered for marker in ASK_MARKERS):
            continue
        cleaned = _text(clause, ASK_MAX_CHARS)
        if cleaned and cleaned not in out:
            out.append(cleaned)
        if len(out) >= MAX_ASKS_PER_REVIEW:
            break
    return out


def parse_reddit_json(payload: dict) -> list[dict]:
    """Reddit's public search .json -> review items. `score` and `ups` are NOT
    read: they are a popularity signal, and this product stores no score."""
    items: list[dict] = []
    children = ((payload or {}).get("data") or {}).get("children") or []
    for child in children:
        data = (child or {}).get("data") or {}
        permalink = _text(data.get("permalink"))
        title = _text(data.get("title"), 200)
        body = _text(data.get("selftext"), 2000)
        if not title and not body:
            continue
        url = ("https://www.reddit.com" + permalink) if permalink.startswith("/") else permalink
        items.append({"review_url": url, "title": title, "body": body})
    return items


_RSS_ITEM = re.compile(r"<item\b.*?</item>", re.S | re.I)


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S | re.I)
    if not m:
        return ""
    raw = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", raw)).strip()


def parse_rss(text: str) -> list[dict]:
    """A minimal RSS/Atom item reader — enough for the feeds in REVIEW_SOURCES,
    with no XML dependency."""
    items: list[dict] = []
    for block in _RSS_ITEM.findall(text or ""):
        title = _tag(block, "title")
        link = _tag(block, "link")
        body = _tag(block, "description") or _tag(block, "content")
        if not link:
            continue
        items.append({"review_url": link, "title": _text(title, 200), "body": _text(body, 2000)})
    return items


def fetch_source(source: dict, query: str, *, fetcher=None, timeout: float = 20.0) -> dict:
    """Fetch one configured provider. Tri-state, exactly like verify.py:

        fetched  — 200 plus parseable items
        skipped  — 401/403/429 (wall / rate limit), any other status, or a
                   network/parse failure. A skip is never a failure.
    """
    fetch = fetcher or netguard.safe_get
    template = source.get("url_template") or ""
    if not template or "{q}" not in template:
        return {"source": source.get("name"), "state": STATE_SKIPPED, "reason": "no usable url_template"}
    url = template.replace("{q}", quote_plus(query))
    try:
        r = fetch(url, headers=UA, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — a wall/network failure is a skip
        return {"source": source.get("name"), "url": url, "state": STATE_SKIPPED, "reason": str(exc)[:120]}
    status = getattr(r, "status_code", None)
    if status in (401, 403, 429):
        return {"source": source.get("name"), "url": url, "state": STATE_SKIPPED,
                "http_status": status, "reason": f"HTTP {status} (walled — listed but not fetched)"}
    if status != 200:
        return {"source": source.get("name"), "url": url, "state": STATE_SKIPPED,
                "http_status": status, "reason": f"HTTP {status}"}
    body = getattr(r, "text", "") or ""
    try:
        if source.get("kind") == "reddit_json":
            items = parse_reddit_json(json.loads(body))
        elif source.get("kind") == "rss":
            items = parse_rss(body)
        else:
            return {"source": source.get("name"), "url": url, "state": STATE_SKIPPED,
                    "reason": f"unknown source kind {source.get('kind')!r}"}
    except Exception as exc:  # noqa: BLE001 — unparseable body is a skip, not a crash
        return {"source": source.get("name"), "url": url, "state": STATE_SKIPPED,
                "http_status": status, "reason": f"unparseable body: {exc}"[:120]}
    return {"source": source.get("name"), "url": url, "state": STATE_FETCHED,
            "http_status": status, "items": items}


def capture(startup, *, sources=None, fetcher=None, timeout: float = 20.0) -> dict:
    """Fetch every configured provider for one competitor.

    Returns {"reviews": [...], "skipped": [...], "sources": [...]} — the shape
    Phase 3's dimension 7 consumes. No aggregate is computed here or anywhere
    else in this module.
    """
    query = _query_for(startup)
    picked = tuple(sources if sources is not None else config.REVIEW_SOURCES)
    result: dict = {"query": query, "reviews": [], "skipped": [], "sources": []}
    for source in picked:
        outcome = fetch_source(source, query, fetcher=fetcher, timeout=timeout)
        result["sources"].append({k: v for k, v in outcome.items() if k != "items"})
        if outcome.get("state") != STATE_FETCHED:
            result["skipped"].append({k: v for k, v in outcome.items() if k != "items"})
            continue
        for item in outcome.get("items") or []:
            text = f"{item.get('title', '')}. {item.get('body', '')}".strip()
            result["reviews"].append({
                "review_url": item.get("review_url"),
                "provider": source.get("name"),
                "title": _text(item.get("title"), 200),
                "excerpt": _text(item.get("body"), EXCERPT_MAX_CHARS),
                "classification": classify(text),
                "asks": extract_asks(text),
                "captured_at": pages_mod.now(),
            })
    return result


def store(conn, startup_id: int, captured: dict) -> int:
    """One evidence row per review, source_url = the review permalink (F-23).

    The extracted asks travel inside that row's `value`, so every ask links to
    the review it came from without a second table and without a score field.
    """
    written = 0
    for review in (captured or {}).get("reviews") or []:
        url = review.get("review_url")
        if not url:
            # No permalink -> nothing to attribute the ask to; skip it rather
            # than store a sourceless claim (write_evidence would refuse anyway).
            continue
        value = json.dumps(
            {"classification": review.get("classification"), "asks": review.get("asks") or []},
            ensure_ascii=False,
        )
        ev.write_evidence(
            conn,
            startup_id,
            "review",
            url,
            claim=review.get("title") or review.get("excerpt") or "(review)",
            value=value,
            provenance="machine_drafted",
            confidence=0.5,
            captured_at=review.get("captured_at") or None,
        )
        written += 1
    return written


def asks_from_evidence(conn, startup_id: int) -> list[dict]:
    """Dimension 7's input, read back out of the evidence rows: every ask with
    the review it came from. Phase 3 consumes this; nothing is scored here."""
    out: list[dict] = []
    for row in ev.for_startup(conn, startup_id, "review"):
        try:
            value = json.loads(row.get("value") or "{}")
        except json.JSONDecodeError:
            continue
        for ask in value.get("asks") or []:
            out.append({
                "ask": ask,
                "source_url": row["source_url"],
                "captured_at": row["captured_at"],
                "classification": value.get("classification"),
            })
    return out
