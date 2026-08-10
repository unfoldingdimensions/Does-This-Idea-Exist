"""Website fetching: homepage text extraction (for LLM description) + Wayback CDX
first-snapshot date (proxy for 'when was this created')."""
import html as html_lib
import logging
import re
from html.parser import HTMLParser

import httpx

from . import netguard

log = logging.getLogger("ideasexist")

UA_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "head"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "head") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.parts.append(t)


def extract_text(html_str: str, max_chars: int = 8000) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html_str)
    except Exception:
        pass
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    return text[:max_chars]


def _meta(html_str: str, name: str) -> str:
    patterns = (
        rf'<meta[^>]+(?:name|property)=["\']{name}["\'][^>]+content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:name|property)=["\']{name}["\']',
    )
    for pat in patterns:
        m = re.search(pat, html_str, re.I)
        if m:
            return html_lib.unescape(m.group(1)).strip()
    return ""


def fetch_homepage(url: str) -> dict:
    """Fetch a homepage; return final_url, title, meta description, visible text.

    Goes through the SSRF guard (netguard.safe_get): only public http(s)
    targets, every redirect hop validated, 2 MB body cap.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    r = netguard.safe_get(url, headers=UA_BROWSER, timeout=25)
    if r.status_code >= 400:
        raise ValueError(f"Website unreachable (HTTP {r.status_code}): {url}")
    text = r.text or ""
    is_html = "text/html" in r.headers.get("content-type", "") or "<html" in text[:2000].lower()
    title = ""
    tm = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    if tm:
        title = html_lib.unescape(tm.group(1)).strip()
    return {
        "final_url": str(r.url),
        "title": title,
        "meta_description": _meta(text, "description"),
        "text": extract_text(text) if is_html else "",
    }


def _normalize_date(raw: str | None) -> str | None:
    """Accept ISO (1997-10-06T...) or compact (19971006 / 19971006000000) → YYYY-MM-DD."""
    raw = (raw or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{4})(\d{2})(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def rdap_registration_date(domain: str) -> str | None:
    """Domain registration date (YYYY-MM-DD) via RDAP bootstrap (rdap.org → TLD server).
    Free, no key. Note: domain registration can predate the company (Notion: 1997 vs 2013)."""
    host = (domain or "").lower().removeprefix("www.").split(":")[0]
    if not host or "." not in host:
        return None
    try:
        r = httpx.get(
            f"https://rdap.org/domain/{host}", timeout=20, headers=UA_BROWSER,
            follow_redirects=True,
        )
        if r.status_code == 200:
            for ev in r.json().get("events", []):
                if ev.get("eventAction") == "registration":
                    d = _normalize_date(ev.get("eventDate"))
                    if d:
                        return d
    except Exception as exc:  # noqa: BLE001 — best-effort lookup; log loudly, return None
        log.warning("rdap lookup failed for %s: %s", host, exc)
    return None


def wayback_first_snapshot(domain: str) -> str | None:
    """First archived snapshot date (YYYY-MM-DD) via the Wayback CDX API, or None.
    CDX 503s transiently — retries and tries both www and bare host variants."""
    candidates = [domain]
    if domain.startswith("www."):
        candidates.append(domain[4:])
    else:
        candidates.append("www." + domain)
    for _ in range(2):
        for cand in candidates:
            try:
                r = httpx.get(
                    "http://web.archive.org/cdx/search/cdx",
                    params={
                        "url": cand,
                        "output": "json",
                        "fl": "timestamp",
                        "filter": "statuscode:200",
                        "collapse": "digest",
                        "limit": "1",
                    },
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    if len(data) > 1 and data[1]:
                        d = _normalize_date(str(data[1][0]))  # CDX: YYYYMMDDHHMMSS
                        if d:
                            return d
            except Exception as exc:  # noqa: BLE001 — best-effort lookup; log loudly, return None
                log.warning("wayback CDX lookup failed for %s: %s", cand, exc)
    return None
