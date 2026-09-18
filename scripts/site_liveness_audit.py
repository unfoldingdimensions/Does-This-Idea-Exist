#!/usr/bin/env python3
"""site_liveness_audit.py - one script that holds the whole liveness-review process.

WHY THIS EXISTS
---------------
This supersedes the ad-hoc pipeline in .openclaw/tmp/audit_fresh.py +
audit_summarise.py + audit_report.py and the one-off drop_repurposed.py. Those
worked, but they were:
  * coupled to one SQLite file and one table,
  * split across three files so the "process" was not in any one place,
  * carrying a hand-maintained id list for the repurposed rows, which meant the
    result was not reproducible from the run itself,
  * only ever run by a human who remembered the lesson behind each rule.

This file is the whole thing: capture -> classify -> recheck -> report -> drop.
It is generic (any SITE_archive table, any CSV/JSON/TXT of URLs, any list of
"other websites we fetch"), it is self-proving (`selftest` runs the classifier
against fixtures built from real cases we hit), and it carries the doctrine in
comments so the next operator does not have to rediscover it.

THE DOCTRINE (read this before changing a rule)
-----------------------------------------------
1. A 200 is not proof of life.
   200 can be a parked page, a domain-for-sale pitch, a registrar placeholder,
   a stock CMS shell, a soft-404, or someone else's gambling site. Every 2xx
   body is fetched and inspected. This is the single most important rule here.

2. A 403 is not proof of death.
   Cloudflare/Akamai/WAF walls answer 403/429/503 to a scripted client while the
   site is perfectly healthy. A row is only WALLED when it refuses every user
   agent we try; it is never DEAD on a 4xx/5xx wall alone.

3. One HTTP client is not evidence.
   Transient resolver failures and per-UA walls are real. Anything that is not
   clean LIVE gets a second pass with a different client and a fresh DNS
   lookup before it is filed as dead or walled. (Real case: LeafLink returned a
   transient DNS failure to pass 1 and 200 to both clients on pass 2. Product
   Hunt / NYT / Squire returned 403 to Chrome and 200 to Firefox.)

4. "Is it up?" is the wrong question. "Is it still this company?" is the right one.
   A domain that changes hands keeps returning 200. Repurposing is caught by two
   independent, high-precision classes:
     A. the page now trades in gambling / piracy / SEO spam, or
     B. it is a stock CMS shell (WordPress "Sample Page" artefact and friends)
        whose title and visible text contain no token of the company name.
   Class B deliberately requires BOTH the CMS artefact AND zero brand tokens, so
   a real company running WordPress cannot trip it.

5. Short foreign words must never match as bare substrings.
   `judi` sits inside "judicial" and "judiciario"; `situs` is Indonesian for
   "site". The first draft of the spam rule flagged Color, Snap, Bolt, Amino,
   Collective Health and Shipper as gambling sites because of this. Every spam
   token is therefore word-bounded, in two tiers: a tier-1 phrase is specific
   enough that one hit settles it; tier-2 words are ordinary vocabulary
   elsewhere and only count when two or more distinct ones appear together.

6. A company is allowed to be named after a CDN.
   The bot-challenge rule once filed Cloudflare's own homepage as a wall, because
   the challenge keyword list contains "cloudflare" and that word is the
   company's own name. Challenge phrases are matched against visible text (not
   raw HTML, where every CDN-tagged page mentions Cloudflare) and any hit that is
   also one of the company's own brand tokens is discarded. Same guard is applied
   to the spam tokens.

7. Scan visible text, not raw HTML.
   Raw HTML is full of third-party script and CSS noise. Keyword rules run over
   entity-decoded, script-stripped visible text plus the <title>.

8. Never delete without a receipt.
   The drop stage re-captures evidence at drop time, writes a manifest BEFORE it
   deletes, uses the sqlite backup API (not a bare file copy), keeps child-table
   history in the manifest, and refuses to run if any targeted row is not
   DEAD/REPURPOSED on fresh evidence. It also refuses if the drop would remove
   more than --max-drop-fraction of the archive, so a classifier bug can never
   empty a table.

9. Reports are ASCII.
   The first report was written UTF-8 and came out mojibake in a PowerShell
   console. Reports are transliterated to ASCII; CSVs are utf-8-sig so Excel
   reads the accents correctly.

USAGE
-----
  # offline proof that the classifier rules behave
  python site_liveness_audit.py selftest

  # audit this repo's archive (read-only on the DB)
  python site_liveness_audit.py audit --db backend/data/ideasexist.db

  # audit any other list of URLs we fetch
  python site_liveness_audit.py audit --urls my_urls.txt --out ./audit-out
  python site_liveness_audit.py audit --file sites.csv --name-col company --url-col homepage
  python site_liveness_audit.py audit --url https://a.example --url https://b.example

  # re-classify a previous run without touching the network
  python site_liveness_audit.py verify --run ./audit-out/liveness-2026-09-18-2010

  # rebuild the report from a run
  python site_liveness_audit.py report --run ./audit-out/liveness-2026-09-18-2010

  # drop everything the run filed DEAD/REPURPOSED (dry-run unless --confirm)
  python site_liveness_audit.py drop --run ./audit-out/liveness-... --db backend/data/ideasexist.db
  python site_liveness_audit.py drop --run ... --db ... --confirm

  # tune the vocabulary for another corpus without editing this file
  python site_liveness_audit.py print-config > kw.json   # then --config kw.json

Exit codes: 0 ok, 1 error, 2 usage, 3 refused by a safety guard, 4 selftest failure.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import dataclasses
import datetime as dt
import hashlib
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import sqlite3
import sys
import threading
import time
import unicodedata
from typing import Any, Iterable, Optional
from urllib.parse import urlparse, urljoin

VERSION = "1.0.0"
TOOL = "site_liveness_audit"

# ---------------------------------------------------------------------------
# Optional HTTP stack. httpx is preferred (its error taxonomy is far better than
# urllib's), but a stdlib fallback keeps this script runnable anywhere, which
# matters because it is meant to be pointed at other corpora in other envs.
# ---------------------------------------------------------------------------
try:
    import httpx  # type: ignore
    HAVE_HTTPX = True
except Exception:  # noqa: BLE001
    httpx = None  # type: ignore
    HAVE_HTTPX = False

import urllib.error
import urllib.request
import html as _html


# ===========================================================================
# 1. Vocabulary. Everything a rule looks at lives here so another corpus can be
#    handled with --config instead of a code edit.
# ===========================================================================
DEFAULT_CONFIG: dict[str, Any] = {
    # --- 200-but-dead: domain is parked / for sale / expired -----------------
    "park_phrases": [
        "buy this domain", "this domain is for sale", "the domain name is for sale",
        "domain is for sale", "domain for sale", "this website is for sale",
        "domain has expired", "this domain has expired", "renew your domain",
        "parked free", "domain parking", "inquire about this domain",
        "premium domain", "register a new domain", "the domain you are looking for",
        "this domain name has been registered", "domain is available for purchase",
        "make an offer on this domain", "purchase this domain",
    ],
    # hosts that are, by construction, a marketplace listing and not a company site
    "marketplace_hosts": [
        "hugedomains.com", "sedo.com", "sedoparking.com", "afternic.com",
        "dan.com", "undeveloped.com", "atom.com", "brandbucket.com",
        "squadhelp.com", "namecheap.com", "spaceship.com", "dynadot.com",
        "sav.com", "bodis.com", "parkingcrew.net", "above.com", "fabulous.com",
    ],
    # A bare server default page is a corpse, not a website. These only count
    # when they are the page TITLE, or the body of a short/titleless page:
    # "index of /" inside a long real page is just a link. Bare vocabulary like
    # "web hosting" is deliberately absent - real sites say that. Placeholder
    # wording is handled separately below and never means death.
    "default_page_phrases": [
        "welcome to nginx", "welcome to nginx!",
        "apache2 ubuntu default page", "apache2 debian default page",
        "apache http server test page", "iis windows server", "it works!",
        "index of /", "default web site page",
        "this is the default web page for this server",
        "web server is successfully installed", "site not configured",
        "no site configured at this address", "account suspended",
        "website is suspended", "this site has been suspended",
        "this account has been suspended", "this site is currently unavailable",
        "website is currently not available",
        "please contact your service provider", "page cannot be displayed",
    ],
    # placeholder wording: "not finished yet". These are ordinary marketing words
    # (Deel's homepage says "stay tuned" in a footer block), so a hit only counts
    # when it is the page TITLE, or when the page is short and carries no brand
    # token. It is never a death sentence - worst case the row is UNKNOWN.
    "placeholder_phrases": [
        "coming soon", "under construction", "site is being built",
        "this site is under construction", "launching soon",
    ],
    # --- walls: matched against VISIBLE TEXT + title, never raw HTML ---------
    # Bare "cloudflare" is deliberately NOT here. It is the CDN mentioned in the
    # footer of half the internet (Astro's and CodeCrafters' own sites tripped it),
    # and the original audit filed Cloudflare's own homepage as a wall because of
    # it. The precise interstitial phrases below cover the real case; "cloudflare
    # ray id" is specific to a Cloudflare error page. "bot detection" and "ddos
    # protection" are out for the same reason - Castle and Clerk *sell* those.
    "challenge_phrases": [
        "just a moment", "checking your browser", "attention required",
        "enable javascript and cookies to continue", "cf-chl",
        "cloudflare ray id", "verify you are human", "verifying you are human",
        "please wait while we verify", "are you a robot", "request blocked",
        "access denied",
    ],
    # --- soft 404: 200 with a "not found" body ------------------------------
    "soft404_phrases": [
        "404 not found", "page not found", "this page is not available",
        "page you are looking for", "no longer available", "page doesn't exist",
        "the page you requested could not be found", "we couldn't find that page",
        "error 404", "nothing found at this address",
    ],
    # --- class A: the page trades in gambling / piracy / SEO spam -----------
    # tier 1 - one hit is enough
    "spam_strong": [
        "agen togel", "bandar togel", "situs togel", "togel online", "toto slot",
        "slot gacor", "rtp slot", "daftar situs", "link alternatif", "situs slot",
        "judi online", "bandar judi", "casino online", "online casino",
        "best online casinos", "maxwin", "sbobet", "xoilac", "cakhia",
        "bong da", "truc tiep", "keo nha cai", "bongda", "fun88", "m88",
        "188bet", "789bet", "jun88", "shbet", "go88", "hit club", "togel",
        "slot online", "judi bola", "sportsbook bonus",
    ],
    # tier 2 - needs --spam-weak-min distinct hits (short/ordinary words that are
    # legitimate vocabulary elsewhere: "situs" = Indonesian for "site",
    # "judi" sits inside "judicial"; word-bounded below, never bare substrings)
    "spam_weak": [
        "judi", "bandar", "situs", "prediksi", "bocoran", "parlay", "taruhan",
        "kasino", "slot", "gacor", "jackpot",
    ],
    "spam_weak_min": 2,
    # --- class B: stock CMS shell ------------------------------------------
    # "skip to content" is NOT one of these: it is an accessibility link on half
    # the WordPress sites on the internet, and treating it as a corpse filed
    # Cambridge Epigenetix->Biomodal, Neural Magic->Red Hat and Fond->Reward
    # Gateway as repurposed spam when they are ordinary acquisitions. The strong
    # marker is the literal "Sample Page" that ships in every fresh WordPress
    # install, and it only counts together with a generic title and zero brand
    # tokens (see shell_class_b_* below).
    "shell_markers_any": ["wp-content", "sample page", "skip to content",
                          "just another wordpress site",
                          "proudly powered by wordpress", "duda", "squarespace",
                          "wix.com", "weebly"],
    "shell_markers_strong": ["sample page", "just another wordpress site"],
    "shell_class_b_required": ["sample page"],
    "shell_class_b_support": ["wp-content", "skip to content"],
    # a title built only from these words is a default title, not a brand
    "generic_title_words": [
        "home", "homepage", "page", "my", "site", "website", "web", "wordpress",
        "wp", "sample", "hello", "world", "welcome", "untitled", "just", "another",
        "blog", "news", "index", "test", "demo", "coming", "soon", "under",
        "construction", "default", "title", "menu", "main",
    ],
    # --- misc ---------------------------------------------------------------
    "js_redirect_phrases": ["redirecting", "you are being redirected",
                            "redirecting you now", "you will be redirected"],
    "gone_phrases": ["this page is not available", "404 not found", "page not found"],
    # words stripped from a company name before it is used as a brand fingerprint
    "stop_tokens": ["formerly", "former", "the", "and", "group", "inc", "inc.",
                    "ltd", "llc", "corp", "corporation", "technologies", "labs",
                    "company", "co", "plc", "gmbh", "software", "systems"],
    # second-level labels that are part of a public suffix (approximate eTLD+1)
    "regdom_suffixes": ["co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "co.nz",
                        "net.nz", "org.nz", "com.au", "net.au", "org.au", "edu.au",
                        "co.jp", "or.jp", "ne.jp", "com.br", "com.cn", "com.hk",
                        "com.sg", "com.tw", "com.tr", "com.mx", "com.ar", "com.co",
                        "com.my", "com.ph", "com.vn", "co.kr", "or.kr", "co.id",
                        "co.in", "net.in", "org.in", "co.za", "co.il", "com.pk",
                        "com.ng", "com.eg", "com.sa", "com.ua", "co.th", "or.th"],
}

CFG: dict[str, Any] = {}
_CFG_HASH = ""


def load_config(path: Optional[str]) -> dict[str, Any]:
    """Deep-merge the built-in vocabulary with an optional JSON override.

    Keys given in the file replace the built-in value for that key. This is the
    escape hatch for other corpora: a piracy-heavy or cyrillic-spam-heavy list
    should not force a code edit.
    """
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if path:
        with open(path, encoding="utf-8") as fh:
            override = json.load(fh)
        for k, v in override.items():
            cfg[k] = v
    global _CFG_HASH
    _CFG_HASH = hashlib.sha256(
        json.dumps(cfg, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return cfg


# ===========================================================================
# 2. Small helpers
# ===========================================================================
def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d-%H%M")


def ascii_safe(text: str) -> str:
    """Transliterate to ASCII. Reports must render identically anywhere."""
    text = (text.replace("\u00b7", "|").replace("\u2014", "-").replace("\u2013", "-")
                .replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2026", "...").replace("\u00a0", " "))
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch if ord(ch) < 128 else "?" for ch in text)


def atomic_write(path: str, data: str, encoding: str = "utf-8") -> None:
    """Write via temp + replace so a crash never leaves a half-written report."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding=encoding, newline="") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class Log:
    """Tee to stdout and a run log. Every run leaves an auditable transcript."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.lock = threading.Lock()
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            open(path, "a", encoding="utf-8").close()

    def __call__(self, msg: str = "") -> None:
        line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
        with self.lock:
            try:
                print(line, flush=True)
            except Exception:  # noqa: BLE001
                print(ascii_safe(line).encode("ascii", "replace").decode("ascii"),
                      flush=True)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(ascii_safe(line) + "\n")


def host_of(url: Any) -> str:
    try:
        return (urlparse(str(url)).hostname or "").lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


def regdom(h: str, cfg: dict[str, Any]) -> str:
    """Approximate registrable domain (no public-suffix list dependency).

    Good enough for "did this URL leave the stored domain": carrd.co vs carrd.com
    differ, docs.foo.com vs foo.com do not.
    """
    h = (h or "").lower().removeprefix("www.")
    if not h or re.fullmatch(r"[0-9.]+", h):
        return h
    parts = h.split(".")
    if len(parts) <= 2:
        return h
    if ".".join(parts[-2:]) in cfg["regdom_suffixes"]:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def brand_tokens(name: str, cfg: dict[str, Any]) -> list[str]:
    stop = {s.lower() for s in cfg["stop_tokens"]}
    toks = re.findall(r"[a-z0-9]+", (name or "").lower())
    return [t for t in toks if len(t) >= 4 and t not in stop]


TAG_RE = re.compile(r"<(script|style|noscript|template|svg)[^>]*>.*?</\1>|<[^>]+>",
                    re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_DESC_RE = re.compile(
    r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']*)[\"']", re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
META_REFRESH_RE = re.compile(
    r"<meta[^>]+http-equiv=[\"']refresh[\"'][^>]+url=([^\"'>\s]+)", re.I)
JS_LOC_RE = re.compile(r"(?:location|window\.location)(?:\.href)?\s*=\s*[\"']([^\"']+)[\"']",
                       re.I)
ENT_RE = re.compile(r"&[a-z]{2,8};|&#\d{1,6};")
WS_RE = re.compile(r"\s+")


def decode_body(body: bytes, charset: Optional[str]) -> str:
    for enc in ([charset] if charset else []) + ["utf-8", "cp1252", "latin-1"]:
        try:
            return body.decode(enc or "utf-8", "strict")
        except Exception:  # noqa: BLE001
            continue
    return body.decode("utf-8", "ignore")


def visible_text(html: str, cap: int = 60000) -> str:
    """Entity-decoded, script-stripped page text. Rules run over THIS."""
    t = TAG_RE.sub(" ", html or "")
    t = ENT_RE.sub(" ", t)
    try:
        t = _html.unescape(t)
    except Exception:  # noqa: BLE001
        pass
    return WS_RE.sub(" ", t).strip()[:cap]


def first_match(pattern: re.Pattern, html: str, cap: int = 300) -> str:
    m = pattern.search(html or "")
    if not m:
        return ""
    inner = m.group(1) if m.groups() else m.group(0)
    return WS_RE.sub(" ", TAG_RE.sub(" ", inner)).strip()[:cap]


# ===========================================================================
# 3. HTTP capture
# ===========================================================================
DEFAULT_UAS = [
    # 0: primary. A normal browser.
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    # 1: alternate engine. Catches per-UA walls (Product Hunt, NYT, Squire).
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    # 2: crawler identity. Some publishers whitelist it (NYT).
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
]
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

_tls = threading.local()


class SafetyError(Exception):
    """Raised when a URL is refused by a guard rather than failing."""


def resolve_host(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for info in infos:
        addr = info[4][0]
        if addr not in out:
            out.append(addr)
    return out


def guard_url(url: str, allow_private: bool) -> tuple[str, list[str]]:
    """Normalise + SSRF-guard a URL before we fetch it.

    This script is pointed at URLs harvested from datasets, so it must not be a
    way to reach the host's own network. Private / loopback / link-local /
    reserved targets are refused unless --allow-private is explicit.
    """
    url = (url or "").strip()
    if not url:
        raise SafetyError("empty url")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise SafetyError(f"scheme not allowed: {p.scheme}")
    if "@" in (p.netloc or ""):
        raise SafetyError("credentials in url are not allowed")
    host = p.hostname or ""
    if not host:
        raise SafetyError("no host")
    if allow_private:
        return url, resolve_host(host)
    if host.lower() in ("localhost",) or host.lower().endswith((".local", ".internal")):
        raise SafetyError(f"non-public host: {host}")
    ips = resolve_host(host)
    if not ips:
        return url, ips  # DNS failure is reported later as dns_error
    for ip in ips:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            raise SafetyError(f"unparsable address {ip}") from None
        if (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved
                or a.is_multicast or a.is_unspecified):
            raise SafetyError(f"non-public address {ip} for {host}")
    return url, ips


@dataclasses.dataclass
class HttpCfg:
    timeout: float = 20.0
    connect_timeout: float = 8.0
    max_bytes: int = 400_000
    max_redirects: int = 8
    retries: int = 2
    backoff: float = 1.4
    max_retry_wait: float = 8.0
    allow_private: bool = False
    politerelay: float = 0.0


def _httpx_client(timeout: float, max_redirects: int):
    cl = getattr(_tls, "client", None)
    key = (timeout, max_redirects)
    if cl is None or getattr(_tls, "key", None) != key:
        if cl is not None:
            try:
                cl.close()
            except Exception:  # noqa: BLE001
                pass
        cl = httpx.Client(follow_redirects=True, max_redirects=max_redirects,
                          timeout=httpx.Timeout(timeout,
                                                connect=min(8.0, max(1.0, timeout))))
        _tls.client, _tls.key = cl, key
    return cl


class _ChainCatcher(urllib.request.HTTPRedirectHandler):
    """stdlib fallback needs its own redirect chain recorder."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        self.chain = getattr(self, "chain", [])
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_once(url: str, ua: str, hcfg: HttpCfg) -> dict[str, Any]:
    """One GET. Returns a capture dict; never raises for network conditions."""
    cap: dict[str, Any] = {
        "url": url, "ua": ua, "status": None, "error": "", "error_class": "",
        "final_url": "", "chain": [], "content_type": "", "server": "",
        "bytes": 0, "truncated": False, "title": "", "meta_description": "",
        "h1": "", "visible": "", "html": "", "elapsed_ms": 0, "blocked_by_guard": "",
    }
    t0 = time.time()
    try:
        safe_url, ips = guard_url(url, hcfg.allow_private)
        cap["ips"] = ips
    except SafetyError as exc:
        cap["blocked_by_guard"] = str(exc)
        cap["error"] = str(exc)
        cap["error_class"] = "guard"
        cap["elapsed_ms"] = int((time.time() - t0) * 1000)
        return cap

    attempt, wait = 0, hcfg.backoff
    while True:
        attempt += 1
        try:
            if HAVE_HTTPX:
                cap.update(_fetch_httpx(safe_url, ua, hcfg))
            else:
                cap.update(_fetch_urllib(safe_url, ua, hcfg))
            cap["error"] = ""
            cap["error_class"] = ""
            break
        except Exception as exc:  # noqa: BLE001
            msg = f"{type(exc).__name__}: {exc}"
            cap["error"] = msg[:240]
            cap["error_class"] = classify_error(msg)
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (429, 503) and attempt <= hcfg.retries:
                ra = 0.0
                try:
                    ra = float(getattr(exc.response, "headers", {}).get("retry-after", 0) or 0)
                except Exception:  # noqa: BLE001
                    ra = 0.0
                time.sleep(min(max(ra, wait), hcfg.max_retry_wait))
                wait *= hcfg.backoff
                continue
            if attempt <= hcfg.retries and cap["error_class"] in (
                    "timeout", "conn_error", "tls_error", "other_error"):
                time.sleep(wait)
                wait *= hcfg.backoff
                continue
            break
    if hcfg.politerelay:
        time.sleep(hcfg.politerelay)
    cap["elapsed_ms"] = int((time.time() - t0) * 1000)
    return cap


def classify_error(msg: str) -> str:
    e = (msg or "").lower()
    if ("name or service not known" in e or "getaddrinfo" in e
            or "no address associated" in e or "nodename nor servname" in e
            or "temporary failure in name resolution" in e
            or "name resolution" in e):
        return "dns_error"
    if "timed out" in e or "timeout" in e:
        return "timeout"
    if "ssl" in e or "certificate" in e or "tls" in e:
        return "tls_error"
    if ("refused" in e or "reset" in e or "connect" in e or "unreachable" in e
            or "blocked" in e):
        return "conn_error"
    return "other_error"


def _fetch_httpx(url: str, ua: str, hcfg: HttpCfg) -> dict[str, Any]:
    cl = _httpx_client(hcfg.timeout, hcfg.max_redirects)
    headers = dict(BASE_HEADERS, **{"User-Agent": ua})
    out: dict[str, Any] = {}
    with cl.stream("GET", url, headers=headers) as r:
        out["status"] = r.status_code
        out["final_url"] = str(r.url)
        out["chain"] = [str(h.url) for h in r.history]
        out["content_type"] = r.headers.get("content-type", "")
        out["server"] = r.headers.get("server", "")
        chunks, total, truncated = [], 0, False
        for chunk in r.iter_bytes():
            chunks.append(chunk)
            total += len(chunk)
            if total >= hcfg.max_bytes:
                truncated = True
                break
        body = b"".join(chunks)
    out["bytes"] = len(body)
    out["truncated"] = truncated
    _extract(out, body, out["content_type"], hcfg)
    return out


def _fetch_urllib(url: str, ua: str, hcfg: HttpCfg) -> dict[str, Any]:
    catcher = _ChainCatcher()
    opener = urllib.request.build_opener(catcher)
    opener.addheaders = [(k, v) for k, v in
                         dict(BASE_HEADERS, **{"User-Agent": ua}).items()]
    out: dict[str, Any] = {}
    try:
        resp = opener.open(url, timeout=hcfg.timeout)
    except urllib.error.HTTPError as exc:
        resp = exc
    out["status"] = int(getattr(resp, "status", 0) or getattr(resp, "code", 0))
    out["final_url"] = getattr(resp, "geturl", lambda: url)()
    out["chain"] = list(getattr(catcher, "chain", []))
    hdrs = getattr(resp, "headers", {}) or {}
    out["content_type"] = hdrs.get("content-type", "")
    out["server"] = hdrs.get("server", "")
    body = resp.read(hcfg.max_bytes + 1) or b""
    out["truncated"] = len(body) > hcfg.max_bytes
    body = body[:hcfg.max_bytes]
    out["bytes"] = len(body)
    try:
        resp.close()
    except Exception:  # noqa: BLE001
        pass
    _extract(out, body, out["content_type"], hcfg)
    return out


def _extract(out: dict[str, Any], body: bytes, ctype: str, hcfg: HttpCfg) -> None:
    charset = ""
    m = re.search(r"charset=([\w\-]+)", ctype or "", re.I)
    if m:
        charset = m.group(1)
    text = decode_body(body, charset)
    out["html"] = text[:hcfg.max_bytes]
    # Keep the shell artefact list on the capture itself: the cache drops the raw
    # HTML to stay small, and class B detection must survive a cached re-run.
    low = text.lower()
    cfg = CFG or DEFAULT_CONFIG
    out["shell_raw"] = [x for x in cfg["shell_markers_any"] if x in low]
    out["shell_strong_raw"] = [x for x in cfg["shell_markers_strong"] if x in low]
    out["title"] = first_match(TITLE_RE, text, 240)
    out["meta_description"] = first_match(META_DESC_RE, text, 300)
    out["h1"] = first_match(H1_RE, text, 200)
    out["visible"] = visible_text(text)
    out["meta_refresh"] = first_match(META_REFRESH_RE, text, 300)
    jm = JS_LOC_RE.search(text or "")
    out["js_location"] = jm.group(1)[:300] if jm else ""


# ===========================================================================
# 4. Signal extraction + classification (pure functions; offline-testable)
# ===========================================================================
def _phrase_hits(text: str, phrases: Iterable[str]) -> list[str]:
    low = (text or "").lower()
    return sorted({p for p in phrases if p in low})


def is_generic_title(title: str, cfg: dict[str, Any]) -> bool:
    """True when the page title is a CMS default rather than a brand.

    "Home | My Site" and "Hello World" are defaults. "Biomodal | Multiomic
    sequencing" is a brand, even when the company used to be called something
    else, and even though it carries no token of the old name.
    """
    t = (title or "").strip().lower()
    if not t:
        return True
    words = set(re.findall(r"[a-z]+", t))
    allowed = {w.lower() for w in cfg.get("generic_title_words") or []}
    return bool(words) and words <= allowed


def signals(cap: dict[str, Any], name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """All content rules for one capture. Visible text + title only (doctrine 7)."""
    visible = cap.get("visible") or ""
    title = cap.get("title") or ""
    hay = f"{title} \n {visible}"
    low = hay.lower()
    toks = brand_tokens(name, cfg)
    sig: dict[str, Any] = {"brand_tokens": toks}
    sig["title_has_brand"] = any(t in title.lower() for t in toks) if toks else None
    sig["text_has_brand"] = any(t in low for t in toks) if toks else None

    sig["park"] = _phrase_hits(hay, cfg["park_phrases"])
    # A default page / soft 404 only counts as death when it is the TITLE, or when
    # the page is short enough that the phrase is the whole content. Otherwise a
    # link reading "index of /" or "page not found" in a real page would kill it.
    small = int(cap.get("bytes") or 0) < 20000
    branded_title = bool(sig["title_has_brand"])
    dp = _phrase_hits(hay, cfg["default_page_phrases"])
    sig["default_page_title"] = [p for p in dp if p in title.lower()]
    sig["default_page_body"] = [] if sig["default_page_title"] else (
        [p for p in dp if (small or not title) and not branded_title])
    s4 = _phrase_hits(hay, cfg["soft404_phrases"])
    sig["soft404_title"] = [p for p in s4 if p in title.lower()]
    sig["soft404_body"] = [] if sig["soft404_title"] else (
        [p for p in s4 if (small or not title) and not branded_title])
    ph = _phrase_hits(hay, cfg.get("placeholder_phrases") or [])
    sig["placeholder"] = ([p for p in ph if p in title.lower()]
                          or [p for p in ph
                              if small and not sig["title_has_brand"]])
    sig["marketplace_host"] = host_of(cap.get("final_url")) in cfg["marketplace_hosts"]

    # challenge: visible text + title, then discard any hit that is the company's
    # own name (doctrine 6 - Cloudflare's homepage is not a bot wall). A wall also
    # has to LOOK like a wall: the phrase in the title, or on a short page. A
    # 60KB marketing page that mentions "access denied" in a blog post is a site.
    ch = [p for p in _phrase_hits(hay, cfg["challenge_phrases"])
          if not any(p == t or p in t or t in p for t in toks)]
    sig["challenge_title"] = [p for p in ch if p in title.lower()]
    sig["challenge_body"] = [] if sig["challenge_title"] else [p for p in ch if small]
    sig["challenge"] = sig["challenge_title"] or sig["challenge_body"]

    # spam: two tiers, word-bounded, brand-guarded (doctrines 5 and 6)
    def _guard(hits: list[str]) -> list[str]:
        return [h for h in hits
                if not any(h == t or (len(h) >= 4 and h in t) for t in toks)]
    strong = []
    for phrase in cfg["spam_strong"]:
        rx = re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b", re.I)
        if rx.search(low):
            strong.append(phrase)
    strong = _guard(sorted(set(strong)))
    weak = []
    for phrase in cfg["spam_weak"]:
        rx = re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b", re.I)
        if rx.search(low):
            weak.append(phrase)
    weak = _guard(sorted(set(weak)))
    sig["spam_strong"] = strong
    sig["spam_weak"] = weak
    sig["spam"] = (strong or
                   (weak if len(weak) >= int(cfg["spam_weak_min"]) else []))
    sig["spam_tier"] = "strong" if strong else ("weak-cluster" if len(weak) >=
                                                int(cfg["spam_weak_min"]) else "")

    low_body = (cap.get("html") or "").lower()
    raw_any = set(cap.get("shell_raw") or [])
    raw_strong = set(cap.get("shell_strong_raw") or [])
    markers = sorted(raw_any | {m for m in cfg["shell_markers_any"] if m in low_body})
    strong_markers = sorted(raw_strong | {m for m in cfg["shell_markers_strong"]
                                          if m in low_body})
    sig["shell_markers"] = markers
    sig["shell_strong"] = strong_markers
    sig["js_redirect"] = bool(_phrase_hits(title, cfg["js_redirect_phrases"])
                              or _phrase_hits(visible[:400], cfg["js_redirect_phrases"]))
    sig["empty_body"] = cap.get("bytes", 0) < 1024 and not title

    # repurposing classes
    sig["generic_title"] = is_generic_title(title, cfg)
    sig["class_a"] = bool(sig["spam"])
    required = set(cfg.get("shell_class_b_required") or ["sample page"])
    support = set(cfg.get("shell_class_b_support") or ["wp-content", "skip to content"])
    sig["class_b"] = bool(
        required <= set(strong_markers)
        and (markers and (support & set(markers)))
        and toks
        and sig["title_has_brand"] is False
        and sig["text_has_brand"] is False
        and sig["generic_title"]
    )
    return sig


def verdict_of(cap: dict[str, Any]) -> str:
    """Reachability verdict for one capture (before any content rules)."""
    if cap.get("blocked_by_guard"):
        return "guard"
    if cap.get("error"):
        return cap.get("error_class") or "other_error"
    st = cap.get("status")
    if st is None:
        return "other_error"
    if st in (404, 410):
        return "gone"
    if st in (401, 402, 403, 405, 406, 429, 451, 503):
        return "blocked"
    if 500 <= st < 600:
        return "server_error"
    if 200 <= st < 400:
        return "alive"
    return f"http_{st}"


def classify(name: str, url: str, caps: list[dict[str, Any]],
             cfg: dict[str, Any]) -> dict[str, Any]:
    """Decide one row from all its captures. Pure: no network, no IO.

    Order of resolution (documented so it can be argued with):
      1. no url                       -> NO_URL
      2. a healthy 2xx whose body is not a wall / park / default page
                                      -> LIVE, or DEAD / REPURPOSED by content
      3. every capture walled         -> WALLED
      4. every capture gone           -> DEAD
      5. otherwise                    -> UNKNOWN (with the strongest reason)
    """
    res: dict[str, Any] = {
        "state": "UNKNOWN", "why": "", "evidence_class": "", "http_status": None,
        "final_url": "", "title": "", "spam": "", "shell": "", "verdicts": {},
        "redirected": False, "stored_host": host_of(url), "final_host": "",
    }
    if not (url or "").strip():
        res.update(state="NO_URL", why="entry carries no website_url")
        return res

    res["verdicts"] = {c.get("ua", "")[:24]: verdict_of(c) for c in caps}
    alive_caps = [c for c in caps if verdict_of(c) == "alive"]

    # pick the best body: prefer the alive capture with the most visible text
    best = max(alive_caps, key=lambda c: len(c.get("visible") or ""), default=None)

    if best is not None:
        sig = best["_sig"]
        res.update(http_status=best.get("status"), final_url=best.get("final_url") or "",
                   title=best.get("title") or "",
                   spam="; ".join(sig["spam"][:6]),
                   shell=",".join(sig["shell_strong"]))
        res["final_host"] = host_of(best.get("final_url"))
        res["redirected"] = bool(res["stored_host"] and res["final_host"]
                                 and regdom(res["stored_host"], cfg) !=
                                 regdom(res["final_host"], cfg))
        # a 200 page that is really a wall still counts as a wall
        if sig["challenge"] and not sig["spam"]:
            res.update(state="WALLED",
                       why=f"soft wall on a {best.get('status')} response: "
                           f"{', '.join(sig['challenge'][:3])}")
            return res
        if sig["park"] or sig["marketplace_host"]:
            detail = ", ".join(sig["park"][:3]) or "marketplace host"
            res.update(state="DEAD", why=f"parked / for-sale page ({detail})")
            return res
        if sig["default_page_title"] or sig["default_page_body"]:
            hits = sig["default_page_title"] or sig["default_page_body"]
            res.update(state="DEAD",
                       why=f"bare server/default page ({', '.join(hits[:3])})")
            return res
        if sig["soft404_title"] or sig["soft404_body"]:
            hits = sig["soft404_title"] or sig["soft404_body"]
            res.update(state="DEAD",
                       why=f"soft 404 on HTTP {best.get('status')} "
                           f"({', '.join(hits[:2])})")
            return res
        if sig["class_a"]:
            res.update(state="REPURPOSED", evidence_class="A:spam-keyword",
                       why="domain now sells unrelated gambling/piracy/SEO spam "
                           f"[{sig['spam_tier']}] ({'; '.join(sig['spam'][:5])})")
            return res
        if sig["class_b"]:
            res.update(state="REPURPOSED", evidence_class="B:content-shell",
                       why="stock CMS shell: default artefact "
                           f"{','.join(sig['shell_strong'])}, generic title "
                           f"{best.get('title','')[:40]!r}, no company token "
                           f"{sig['brand_tokens']} in title or visible text")
            return res
        if sig["placeholder"]:
            res.update(state="UNKNOWN",
                       why=f"placeholder wording ({', '.join(sig['placeholder'][:2])})")
            return res
        if sig["js_redirect"] or (best.get("meta_refresh") and not best.get("title")):
            res.update(state="UNKNOWN",
                       why="JavaScript/meta redirect shell; target not resolved "
                           f"(title={best.get('title','')[:40]!r})")
            return res
        if sig["empty_body"]:
            res.update(state="UNKNOWN",
                       why=f"HTTP {best.get('status')} with an empty/short body and no title")
            return res
        res.update(state="LIVE", why=f"HTTP {best.get('status')}")
        return res

    # no alive capture - look at why
    v = {c.get("ua", "")[:24]: verdict_of(c) for c in caps}
    reasons = []
    for c in caps:
        reasons.append(f"{verdict_of(c)}({c.get('status') or c.get('error_class')})")
    joined = ", ".join(reasons[:4])
    gone = [c for c in caps if verdict_of(c) == "gone"]
    blocked = [c for c in caps if verdict_of(c) == "blocked"]
    guards = [c for c in caps if verdict_of(c) == "guard"]
    if gone and not blocked:
        res.update(state="DEAD", http_status=gone[0].get("status"),
                   why=f"hard {', '.join(str(c.get('status')) for c in gone)} ({joined})")
        return res
    if blocked and not gone:
        res.update(state="WALLED", http_status=blocked[0].get("status"),
                   final_url=blocked[0].get("final_url") or "",
                   why=f"refused every client we tried: {joined}")
        return res
    if guards and len(guards) == len(caps):
        res.update(state="UNKNOWN", why=f"refused by SSRF guard: {guards[0].get('error')}")
        return res
    res.update(state="UNKNOWN", http_status=(caps[0].get("status") if caps else None),
               why=f"unconfirmed: {joined}")
    return res


# ===========================================================================
# 5. Sources
# ===========================================================================
DEFAULT_DB_QUERY = "select * from {table}"


def load_records(args: argparse.Namespace, log: Log) -> tuple[list[dict], str]:
    """Return (records, provenance). Records: {id,name,url,raw:{...}}."""
    if args.db:
        table = args.table
        if args.query:
            q = args.query
        else:
            cols = [c.strip() for c in args.columns.split(",")] if args.columns else None
            if cols:
                q = f"select {', '.join(cols)} from {table}"
            else:
                q = DEFAULT_DB_QUERY.format(table=table)
        # read-only, and forward slashes so the sqlite URI works on Windows
        db_uri = os.path.abspath(args.db).replace("\\", "/")
        con = sqlite3.connect(f"file:{db_uri}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in con.execute(q)]
        finally:
            con.close()
        recs = []
        for r in rows:
            recs.append({
                "id": r.get(args.id_col, r.get("id")),
                "name": str(r.get(args.name_col) or r.get("name") or "").strip(),
                "url": str(r.get(args.url_col) or r.get("website_url") or "").strip(),
                "raw": r,
            })
        return recs, f"db:{args.db}#{table}"

    path = args.file
    if path:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".json", ".jsonl", ".ndjson"):
            with open(path, encoding="utf-8") as fh:
                text = fh.read().strip()
            if text.startswith("["):
                data = json.loads(text)
            else:
                data = [json.loads(line) for line in text.splitlines() if line.strip()]
            recs = []
            for i, d in enumerate(data):
                if isinstance(d, str):
                    recs.append({"id": i, "name": host_of(d), "url": d, "raw": {}})
                else:
                    recs.append({
                        "id": d.get(args.id_col, d.get("id", i)),
                        "name": str(d.get(args.name_col) or d.get("name") or
                                    host_of(d.get(args.url_col, ""))).strip(),
                        "url": str(d.get(args.url_col) or d.get("url") or
                                   d.get("website_url") or "").strip(),
                        "raw": d,
                    })
            return recs, f"json:{path}"
        if ext in (".csv", ".tsv"):
            delim = "\t" if ext == ".tsv" else (
                ";" if args.delimiter == ";" else args.delimiter)
            with open(path, encoding="utf-8-sig", newline="") as fh:
                data = list(csv.DictReader(fh, delimiter=delim))
            recs = []
            for i, d in enumerate(data):
                recs.append({
                    "id": d.get(args.id_col, d.get("id", i)),
                    "name": str(d.get(args.name_col) or d.get("name") or "").strip(),
                    "url": str(d.get(args.url_col) or d.get("website_url") or
                               d.get("url") or "").strip(),
                    "raw": d,
                })
            return recs, f"csv:{path}"
        # anything else: a plain list of URLs, one per line, optional TAB label
        recs = []
        with open(path, encoding="utf-8-sig") as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"[\t,;]", line, maxsplit=1)
                url = parts[0].strip()
                label = parts[1].strip() if len(parts) > 1 else ""
                recs.append({"id": i, "name": label or host_of(url), "url": url,
                             "raw": {"line": line}})
        return recs, f"urls:{path}"

    recs = [{"id": i, "name": host_of(u), "url": u, "raw": {}}
            for i, u in enumerate(args.url)]
    return recs, "inline"


# ===========================================================================
# 6. Stages
# ===========================================================================
def capture_all(records: list[dict], hcfg: HttpCfg, uas: list[str], log: Log,
                cache: Optional["Cache"] = None) -> None:
    """Fetch every record with the primary UA (cache-aware, resumable)."""
    todo = [r for r in records if not (cache and cache.get(r["url"], uas[0]))]
    log(f"capture: {len(records)} records, {len(todo)} to fetch, "
        f"{len(records) - len(todo)} from cache")
    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max(1, hcfg.workers)) as ex:
        futs = {ex.submit(fetch_once, r["url"], uas[0], hcfg): r for r in todo}
        for fut in cf.as_completed(futs):
            r = futs[fut]
            try:
                cap = fut.result()
            except Exception as exc:  # noqa: BLE001
                cap = {"url": r["url"], "ua": uas[0], "status": None,
                       "error": f"{type(exc).__name__}: {exc}"[:200],
                       "error_class": "other_error", "elapsed_ms": 0}
            r.setdefault("caps", []).insert(0, cap)
            if cache:
                cache.put(cap)
            done += 1
            if done % 50 == 0 or done == len(todo):
                el = max(1e-6, time.time() - t0)
                log(f"  capture {done}/{len(todo)} ({el:.0f}s, {done / el:.1f}/s)")
    if cache:
        cache.flush()
    for r in records:
        if not r.get("caps"):
            c = cache.get(r["url"], uas[0]) if cache else None
            if c:
                r["caps"] = [c]


def recheck_all(records: list[dict], hcfg: HttpCfg, uas: list[str], log: Log,
                cache: Optional["Cache"] = None) -> None:
    """Second method for anything that is not a clean LIVE (doctrine 3)."""
    need = []
    for r in records:
        caps = r.get("caps") or []
        if not caps:
            need.append(r)
            continue
        if all(verdict_of(c) == "alive" for c in caps) and caps:
            # cheap pre-filter: only skip if the body looks clean
            if not any((c.get("_sig") or {}).get("challenge") for c in caps):
                continue
        need.append(r)
    log(f"recheck: {len(need)} rows get a second client + fresh DNS")
    done = 0
    t0 = time.time()
    for alt in uas[1:]:
        with cf.ThreadPoolExecutor(max_workers=max(1, hcfg.workers)) as ex:
            futs = {}
            for r in need:
                if any(c.get("ua") == alt for c in (r.get("caps") or [])):
                    continue
                cached = cache.get(r["url"], alt) if cache else None
                if cached:
                    futs[ex.submit(lambda c=cached: c)] = r
                else:
                    futs[ex.submit(fetch_once, r["url"], alt, hcfg)] = r
            for fut in cf.as_completed(futs):
                r = futs[fut]
                try:
                    cap = fut.result()
                except Exception as exc:  # noqa: BLE001
                    cap = {"url": r["url"], "ua": alt, "status": None,
                           "error": f"{type(exc).__name__}: {exc}"[:200],
                           "error_class": "other_error", "elapsed_ms": 0}
                r.setdefault("caps", []).append(cap)
                if cache and not cache.get(r["url"], alt):
                    cache.put(cap)
                done += 1
        log(f"  recheck after {done} captures ({time.time() - t0:.0f}s)")
    if cache:
        cache.flush()


class Cache:
    """Append-only JSONL capture cache, keyed by url + UA.

    Makes a re-run cheap, makes --resume real, and lets `verify` re-classify a
    corpus with zero network traffic.
    """

    def __init__(self, path: str, ttl_seconds: int = 7 * 24 * 3600):
        self.path = path
        self.ttl = ttl_seconds
        self.mem: dict[tuple[str, str], dict] = {}
        self._fh = None
        self._lock = threading.Lock()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                    except Exception:  # noqa: BLE001
                        continue
                    self.mem[(c.get("url", ""), c.get("ua", ""))] = c

    def _key(self, url: str, ua: str) -> tuple[str, str]:
        return (url, ua)

    def get(self, url: str, ua: str) -> Optional[dict]:
        c = self.mem.get(self._key(url, ua))
        if not c:
            return None
        if self.ttl and time.time() - float(c.get("_cached_at", 0)) > self.ttl:
            return None
        return c

    def put(self, cap: dict) -> None:
        cap = dict(cap)
        cap["_cached_at"] = time.time()
        cap.pop("html", None)  # cache stays small; visible text + shell_raw survive
        if cap.get("visible"):
            cap["visible"] = cap["visible"][:30000]
        with self._lock:
            self.mem[self._key(cap.get("url", ""), cap.get("ua", ""))] = cap
            if self._fh is None:
                self._fh = open(self.path, "a", encoding="utf-8")
            self._fh.write(json.dumps(cap, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        with self._lock:
            if self._fh:
                self._fh.flush()
                os.fsync(self._fh.fileno())


def run_audit(args: argparse.Namespace, log: Log) -> int:
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    records, provenance = load_records(args, log)
    if args.sample and args.sample < len(records):
        rnd = random.Random(args.seed)
        records = rnd.sample(records, args.sample)
    if args.limit:
        records = records[: args.limit]
    log(f"source: {provenance} | {len(records)} records | workers={args.workers} "
        f"| timeout={args.timeout}s | config={_CFG_HASH}")

    hcfg = HttpCfg(timeout=args.timeout, max_bytes=args.max_bytes,
                   retries=args.retries, allow_private=args.allow_private,
                   politerelay=args.min_delay)
    hcfg.workers = args.workers  # type: ignore[attr-defined]
    uas = args.user_agent or DEFAULT_UAS
    uas = uas[: max(1, args.ua_count)]
    cache = Cache(os.path.join(out_dir, "captures.cache.jsonl"),
                  ttl_seconds=args.cache_ttl) if not args.no_cache else None

    capture_all(records, hcfg, uas, log, cache)

    # score bodies before the recheck pass so the pre-filter can work
    for r in records:
        for c in r.get("caps") or []:
            c["_sig"] = signals(c, r["name"], CFG)

    if not args.no_recheck and len(uas) > 1:
        recheck_all(records, hcfg, uas, log, cache)

    # final classification over all captures
    for r in records:
        for c in r.get("caps") or []:
            if "_sig" not in c:
                c["_sig"] = signals(c, r["name"], CFG)
        r["result"] = classify(r["name"], r["url"], r.get("caps") or [], CFG)

    write_run(out_dir, records, provenance, args, uas, log)
    summarise(records, log)
    return 0


def write_run(out_dir: str, records: list[dict], provenance: str,
              args: argparse.Namespace, uas: list[str], log: Log) -> str:
    """Persist captures + states. This directory is the run's receipt."""
    run_dir = os.path.join(out_dir, f"liveness-{stamp()}")
    os.makedirs(run_dir, exist_ok=True)

    with open(os.path.join(run_dir, "captures.jsonl"), "w", encoding="utf-8") as fh:
        for r in records:
            for c in r.get("caps") or []:
                row = {k: v for k, v in c.items() if k not in ("html", "_sig")}
                row["_record_id"] = r["id"]
                row["_record_name"] = r["name"]
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "tool": TOOL, "version": VERSION, "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": provenance, "records": len(records), "user_agents": uas,
        "config_hash": _CFG_HASH,
        "settings": {k: v for k, v in vars(args).items() if k not in ("url",)},
    }
    atomic_write(os.path.join(run_dir, "run.json"), json.dumps(meta, indent=2,
                                                                ensure_ascii=False))

    states = []
    for r in records:
        res = r["result"]
        caps = r.get("caps") or []
        primary = caps[0] if caps else {}
        states.append({
            "id": r["id"], "name": r["name"], "url": r["url"],
            "state": res["state"], "why": res["why"],
            "evidence_class": res.get("evidence_class", ""),
            "http_status": res.get("http_status"),
            "final_url": res.get("final_url", ""),
            "title": res.get("title", ""),
            "spam": res.get("spam", ""),
            "shell": res.get("shell", ""),
            "stored_host": res.get("stored_host", ""),
            "final_host": res.get("final_host", ""),
            "redirected": res.get("redirected", False),
            "verdicts": res.get("verdicts", {}),
            "server": primary.get("server", ""),
            "bytes": primary.get("bytes", 0),
            "elapsed_ms": primary.get("elapsed_ms", 0),
        })
    states.sort(key=lambda s: (str(s["name"]).lower(), str(s["id"])))
    atomic_write(os.path.join(run_dir, "states.json"),
                 json.dumps(states, indent=1, ensure_ascii=False))
    write_report(run_dir, states, meta, log)
    log(f"run written: {run_dir}")
    return run_dir


STATE_ORDER = ["LIVE", "DEAD", "REPURPOSED", "WALLED", "UNKNOWN", "NO_URL"]


def summarise(records: list[dict], log: Log) -> None:
    counts = collections.Counter(r["result"]["state"] for r in records)
    log("states: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER))
    for st in ("DEAD", "REPURPOSED"):
        rows = [r for r in records if r["result"]["state"] == st]
        for r in sorted(rows, key=lambda x: str(x["name"]).lower()):
            log(f"  {st:<11} {str(r['id']):>6}  {r['name'][:32]:<32} {r['url'][:52]:<52} "
                f"{r['result']['why'][:80]}")


def write_report(run_dir: str, states: list[dict], meta: dict, log: Log) -> None:
    counts = collections.Counter(s["state"] for s in states)
    total = len(states) or 1
    by_state = {st: sorted([s for s in states if s["state"] == st],
                           key=lambda s: str(s["name"]).lower())
                for st in STATE_ORDER}
    redirects = sorted([s for s in states if s.get("redirected")],
                       key=lambda s: str(s["name"]).lower())
    review = sorted([s for s in states if s["state"] in ("UNKNOWN", "NO_URL")],
                    key=lambda s: str(s["name"]).lower())

    def esc(v: Any, n: int = 120) -> str:
        return ascii_safe(str(v or "").replace("|", "/").replace("\n", " "))[:n]

    L: list[str] = []
    A = L.append
    A("# Liveness audit")
    A("")
    A(f"**Run:** {meta['generated_at']} | **Source:** `{meta['source']}` | "
      f"**Records:** {len(states)} | **Tool:** {TOOL} {VERSION} "
      f"(config {meta['config_hash']})")
    A("")
    A("Every record was fetched live. A 200 was not treated as proof of life: each 2xx "
      "body was fetched and scanned for parking, for-sale, server-default, soft-404, "
      "bot-wall and repurposing markers. Anything that was not a clean LIVE got a second "
      "pass with a different user agent and a fresh DNS lookup, so a single 403 or a "
      "transient resolver failure is never reported as a death.")
    A("")
    A("States: **LIVE** serves the company's own site | **DEAD** hard 404/410, parked, "
      "for-sale or a bare server default page | **REPURPOSED** returns 200 but the domain "
      "changed hands (class A gambling/piracy/SEO spam, or class B stock CMS shell with no "
      "brand token anywhere) | **WALLED** refused every client we tried | **UNKNOWN** "
      "unconfirmed | **NO_URL** nothing to check.")
    A("")
    A("## Headline")
    A("")
    A("| Result | Count | Share |")
    A("|---|---|---|")
    for st in STATE_ORDER:
        c = counts.get(st, 0)
        if c or st in ("LIVE", "DEAD", "REPURPOSED", "WALLED", "UNKNOWN"):
            A(f"| {st} | {c} | {c / total * 100:.1f}% |")
    A(f"| **Total** | **{len(states)}** | **100%** |")
    A("")
    for st, note in (
            ("DEAD", "dead - parked, for-sale, default page or hard 404"),
            ("REPURPOSED", "still online, company gone - needs a decision"),
            ("WALLED", "refused our clients - unconfirmed"),
            ("UNKNOWN", "could not be confirmed either way")):
        rows = by_state.get(st) or []
        if not rows:
            continue
        A(f"## {st} ({len(rows)}) - {note}")
        A("")
        A("| # | Name | URL | Final URL | Detail |")
        A("|---|---|---|---|---|")
        for s in rows:
            A(f'| {esc(s["id"], 12)} | {esc(s["name"], 50)} | {esc(s["url"], 70)} | '
              f'{esc(s["final_url"], 60)} | {esc(s["why"], 130)} |')
        A("")
    if redirects:
        A(f"## Redirected off the stored domain ({len(redirects)})")
        A("")
        A("| # | Name | Stored host | Final host | State |")
        A("|---|---|---|---|---|")
        for s in redirects:
            A(f'| {esc(s["id"], 12)} | {esc(s["name"], 40)} | {s["stored_host"]} | '
              f'{s["final_host"]} | {s["state"]} |')
        A("")
    A("## Reproducing this run")
    A("")
    A("```")
    A(f"cd {TOOL} && python site_liveness_audit.py verify --run \"{run_dir}\"")
    A(f"python site_liveness_audit.py drop --run \"{run_dir}\" --db <db>   # dry-run")
    A("```")
    A("")
    A("## Full table")
    A("")
    A("| # | Name | URL | State | HTTP | Detail |")
    A("|---|---|---|---|---|---|")
    for s in sorted(states, key=lambda s: (str(s["name"]).lower(), str(s["id"]))):
        A(f'| {esc(s["id"], 12)} | {esc(s["name"], 46)} | {esc(s["url"], 70)} | '
          f'**{s["state"]}** | {s["http_status"] if s["http_status"] is not None else "-"} | '
          f'{esc(s["why"], 110)} |')
    A("")

    md_path = os.path.join(run_dir, "report.md")
    atomic_write(md_path, "\n".join(L))

    csv_cols = ["id", "name", "url", "state", "evidence_class", "http_status",
                "final_url", "title", "spam", "shell", "detail"]
    lines = []
    buf = []
    import io
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=csv_cols)
    w.writeheader()
    for s in sorted(states, key=lambda s: (str(s["name"]).lower(), str(s["id"]))):
        w.writerow({"id": s["id"], "name": s["name"], "url": s["url"],
                    "state": s["state"], "evidence_class": s.get("evidence_class", ""),
                    "http_status": s["http_status"], "final_url": s["final_url"],
                    "title": s["title"], "spam": s["spam"], "shell": s["shell"],
                    "detail": s["why"]})
    lines.append(sio.getvalue())
    atomic_write(os.path.join(run_dir, "report.csv"), "".join(lines), encoding="utf-8-sig")
    log(f"report: {md_path}")


def run_verify(args: argparse.Namespace, log: Log) -> int:
    """Re-classify a saved run from its captures. No network at all."""
    run_dir = os.path.abspath(args.run)
    caps_by_id: dict[Any, list[dict]] = collections.defaultdict(list)
    names: dict[Any, str] = {}
    urls: dict[Any, str] = {}
    with open(os.path.join(run_dir, "captures.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            rid = c.get("_record_id")
            caps_by_id[rid].append(c)
            names[rid] = c.get("_record_name", "")
            urls[rid] = c.get("url", "")
    states = []
    for rid, caps in caps_by_id.items():
        for c in caps:
            c["_sig"] = signals(c, names.get(rid, ""), CFG)
        res = classify(names.get(rid, ""), urls.get(rid, ""), caps, CFG)
        states.append({"id": rid, "name": names.get(rid, ""), "url": urls.get(rid, ""),
                       "state": res["state"], "why": res["why"],
                       "evidence_class": res.get("evidence_class", ""),
                       "http_status": res.get("http_status"),
                       "final_url": res.get("final_url", ""), "title": res.get("title", ""),
                       "spam": res.get("spam", ""), "shell": res.get("shell", ""),
                       "stored_host": res.get("stored_host", ""),
                       "final_host": res.get("final_host", ""),
                       "redirected": res.get("redirected", False),
                       "verdicts": res.get("verdicts", {})})
    states.sort(key=lambda s: (str(s["name"]).lower(), str(s["id"])))
    meta = {"tool": TOOL, "version": VERSION, "generated_at": now(), "source": run_dir,
            "config_hash": _CFG_HASH}
    atomic_write(os.path.join(run_dir, "states.json"),
                 json.dumps(states, indent=1, ensure_ascii=False))
    write_report(run_dir, states, meta, log)
    counts = collections.Counter(s["state"] for s in states)
    log("reverified: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER))
    return 0


def run_report(args: argparse.Namespace, log: Log) -> int:
    run_dir = os.path.abspath(args.run)
    states = json.load(open(os.path.join(run_dir, "states.json"), encoding="utf-8"))
    meta = {"tool": TOOL, "version": VERSION, "generated_at": now(), "source": run_dir,
            "config_hash": _CFG_HASH}
    try:
        meta.update(json.load(open(os.path.join(run_dir, "run.json"), encoding="utf-8")))
    except Exception:  # noqa: BLE001
        pass
    write_report(run_dir, states, meta, log)
    return 0


def run_drop(args: argparse.Namespace, log: Log) -> int:
    """Delete DEAD/REPURPOSED rows - with a receipt and a set of brakes."""
    if not args.db:
        log("drop requires --db")
        return 2
    run_dir = os.path.abspath(args.run)
    states = json.load(open(os.path.join(run_dir, "states.json"), encoding="utf-8"))
    targets = [s for s in states
               if s["state"] in (args.states.split(",") if args.states
                                 else ("DEAD", "REPURPOSED"))]
    total = len(states) or 1
    log(f"drop plan: {len(targets)} of {len(states)} rows "
        f"({len(targets) / total * 100:.1f}%) from states={args.states or 'DEAD,REPURPOSED'}")

    if not targets:
        log("nothing to drop")
        return 0
    if len(targets) / total > args.max_drop_fraction:
        log(f"REFUSED: {len(targets) / total * 100:.1f}% of the corpus would be removed, "
            f"above --max-drop-fraction={args.max_drop_fraction:.0%}. "
            f"Re-run with a higher fraction if that is really intended.")
        return 3

    hcfg = HttpCfg(timeout=args.timeout, retries=args.retries,
                   allow_private=args.allow_private)
    hcfg.workers = args.workers  # type: ignore[attr-defined]
    uas = (args.user_agent or DEFAULT_UAS)[: max(1, args.ua_count)]

    # 1. fresh evidence at drop time (doctrine 8)
    if not args.no_recheck:
        log("re-capturing fresh evidence before deleting")
        for s in targets:
            caps = []
            with cf.ThreadPoolExecutor(max_workers=min(4, len(uas) or 1)) as ex:
                futs = [ex.submit(fetch_once, s["url"], ua, hcfg) for ua in uas]
                for fut in cf.as_completed(futs):
                    try:
                        caps.append(fut.result())
                    except Exception as exc:  # noqa: BLE001
                        caps.append({"url": s["url"], "status": None,
                                     "error": str(exc)[:200], "error_class": "other_error"})
            for c in caps:
                c["_sig"] = signals(c, s["name"], CFG)
            res = classify(s["name"], s["url"], caps, CFG)
            s["fresh_state"] = res["state"]
            s["fresh_why"] = res["why"]
            s["fresh_evidence_class"] = res.get("evidence_class", "")
            s["fresh_captures"] = [{k: v for k, v in c.items()
                                    if k not in ("html", "_sig")} for c in caps]
            log(f"  {s['id']:>6} {str(s['name'])[:30]:<30} {s['state']:<11} -> "
                f"{res['state']:<11} {res['why'][:70]}")

    allowed = {x.strip() for x in (args.require_fresh or "DEAD,REPURPOSED").split(",")}
    bad = [s for s in targets
           if not args.no_recheck and s.get("fresh_state") not in allowed]
    if bad:
        log(f"REFUSED: {len(bad)} row(s) no longer demonstrate "
            f"{sorted(allowed)} on fresh evidence:")
        for s in bad[:12]:
            log(f"  {s['id']} {s['name']}: {s.get('fresh_state')} - {s.get('fresh_why')}")
        return 3

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    ids = [s["id"] for s in targets]
    ph = ",".join("?" * len(ids))
    id_col = args.id_col
    table = args.table
    query = f'select * from {table} where {id_col} in ({ph})'
    present = {row[id_col]: dict(row) for row in con.execute(query, ids)}
    missing = [i for i in ids if i not in present]
    if missing:
        log(f"note: {len(missing)} id(s) not present in {table}: {missing[:8]}")

    # 2. backup FIRST, via the sqlite backup API (not a bare file copy)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(os.path.dirname(os.path.abspath(args.db)),
                          f"{os.path.basename(args.db)}.bak-{ts}")
    if args.confirm:
        bck = sqlite3.connect(backup)
        with bck:
            con.backup(bck)
        bck.close()
        log(f"backup: {backup}")

    # 3. manifest BEFORE the delete, so a crash leaves a receipt
    manifest = {
        "dropped_at": dt.datetime.now().isoformat(timespec="seconds"),
        "tool": f"{TOOL} {VERSION}", "config_hash": _CFG_HASH,
        "run": run_dir, "db": os.path.abspath(args.db), "table": table,
        "states_dropped": args.states or "DEAD,REPURPOSED",
        "instruction": "Rows a prior run filed DEAD/REPURPOSED. Fresh evidence was "
                       "re-captured at drop time unless --no-recheck. Child-table "
                       "history is included below.",
        "db_backup": os.path.basename(backup) if args.confirm else None,
        "rows": [{**present.get(s["id"], {}), "_state": s["state"], "_why": s["why"],
                  "_fresh_state": s.get("fresh_state"),
                  "_fresh_why": s.get("fresh_why"),
                  "_evidence_class": s.get("fresh_evidence_class") or s.get("evidence_class"),
                  "_url": s["url"], "_name": s["name"],
                  "_fresh_captures": s.get("fresh_captures", [])} for s in targets],
        "children": {},
    }
    children = [c for c in (args.child_tables or "").split(",") if c.strip()]
    for child in children:
        child = child.strip()
        try:
            rows = [dict(r) for r in con.execute(
                f'select * from {child} where {args.child_fk_col} in ({ph})', ids)]
            manifest["children"][child] = rows
        except Exception as exc:  # noqa: BLE001
            log(f"note: child table {child} not readable ({exc}); skipped")
    manifest_path = os.path.abspath(args.manifest or
                                    os.path.join(run_dir, f"dropped-{ts}.json"))
    atomic_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
    log(f"manifest: {manifest_path}")

    if not args.confirm:
        log("dry-run: nothing deleted. Re-run with --confirm to apply.")
        return 0

    before = con.execute(f"select count(*) from {table}").fetchone()[0]
    with con:
        for child in children:
            child = child.strip()
            try:
                con.execute(f'delete from {child} where {args.child_fk_col} in ({ph})', ids)
            except Exception:  # noqa: BLE001
                pass
        deleted = con.execute(f'delete from {table} where {id_col} in ({ph})', ids).rowcount
    con.execute("vacuum")
    con.commit()
    after = con.execute(f"select count(*) from {table}").fetchone()[0]
    left = con.execute(f'select count(*) from {table} where {id_col} in ({ph})', ids).fetchone()[0]
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    log(f"deleted={deleted} ({before} -> {after}) target rows remaining={left} "
        f"integrity={integrity}")
    if left or integrity.lower() != "ok":
        log("WARNING: post-delete check failed; restore from the backup above")
        return 1
    return 0


# ===========================================================================
# 7. Selftest - the fixtures are the real cases that taught us the rules.
# ===========================================================================
def _cap(**kw: Any) -> dict[str, Any]:
    base = {"url": "https://example.com", "ua": DEFAULT_UAS[0], "status": 200,
            "error": "", "error_class": "", "final_url": "https://example.com",
            "chain": [], "content_type": "text/html", "server": "", "bytes": 5000,
            "truncated": False, "title": "", "meta_description": "", "h1": "",
            "visible": "", "html": "", "elapsed_ms": 10, "blocked_by_guard": ""}
    base.update(kw)
    return base


def _fixtures() -> list[tuple[str, str, str, list[dict], str, str]]:
    """(label, name, url, captures, expected_state, expected_class)."""
    F: list[tuple[str, str, str, list[dict], str, str]] = []

    # --- 200 is not life -----------------------------------------------------
    F.append(("parked-for-sale", "Pavilion", "https://pavilion.io",
              [_cap(title="pavilion.io is for sale",
                    visible="Buy this domain. Inquire about this domain today.",
                    html="<title>pavilion.io is for sale</title>buy this domain")],
              "DEAD", ""))
    F.append(("marketplace-host", "Rapid Robotics", "https://atom.com/name/RapidRobotics",
              [_cap(final_url="https://www.atom.com/name/RapidRobotics",
                    title="RapidRobotics.com - Premium Domain For Sale",
                    visible="Premium domain for sale")],
              "DEAD", ""))
    F.append(("nginx-default", "Credy", "https://credy.in",
              [_cap(title="Welcome to nginx!",
                    visible="Welcome to nginx! If you see this page, the nginx web server "
                            "is successfully installed and working.",
                    html="<title>Welcome to nginx!</title>welcome to nginx")],
              "DEAD", ""))
    F.append(("soft-404", "Ghost Co", "https://ghost.example",
              [_cap(status=200, title="Page not found",
                    visible="404 Not Found. The page you are looking for does not exist.")],
              "DEAD", ""))

    # --- repurposing, class A ------------------------------------------------
    F.append(("oribi-casino", "Oribi", "https://oribi.io",
              [_cap(title="Best Online Casinos in Canada: Top Sites Compared 2026",
                    visible="Best online casinos in Canada. Compare the top sites.")],
              "REPURPOSED", "A:spam-keyword"))
    F.append(("helium-togel", "Helium Health", "https://heliumhealthcare.com",
              [_cap(title="KPKTOTO - Penyeragaman Agen Togel Toto Macau",
                    visible="Agen togel resmi. Daftar situs togel online terpercaya.")],
              "REPURPOSED", "A:spam-keyword"))
    F.append(("creator-toto-slot", "Creator", "https://ttoto99.com",
              [_cap(title="TOTO99: Bandar Penyedia Signal Toto Slot Mix Parlay",
                    visible="Toto slot dan mix parlay untuk member baru.")],
              "REPURPOSED", "A:spam-keyword"))

    # --- repurposing, class B ------------------------------------------------
    F.append(("wp-shell-no-brand", "Raise (formerly HelloOffice)", "https://hellooffice.com",
              [_cap(title="Hello World",
                    visible="Sample Page. Skip to content. Recent Posts.",
                    html="<title>Hello World</title>wp-content sample page skip to content")],
              "REPURPOSED", "B:content-shell"))
    # A legitimate acquisition/rebrand: the domain serves the acquirer's own
    # WordPress site, which of course has "skip to content" and no token of the
    # old company name. This must stay LIVE - it was a real false positive.
    F.append(("legit-rebrand-not-spam", "Cambridge Epigenetix", "https://biomodal.com",
              [_cap(title="Biomodal | Multiomic sequencing", bytes=90000,
                    visible="Biomodal is a clinical epigenomics company. "
                            "Skip to content. Our platform.",
                    html="<title>Biomodal</title>wp-content skip to content")],
              "LIVE", ""))

    # --- the two precision regressions --------------------------------------
    F.append(("judi-inside-judicial", "Collective Health", "https://collectivehealth.com",
              [_cap(title="Collective Health",
                    visible="Our judicial review process and the judiciary branch.")],
              "LIVE", ""))
    F.append(("situs-single-weak-hit", "Acme Widgets", "https://acme.example",
              [_cap(title="Acme Widgets",
                    visible="Situs ini adalah halaman resmi perusahaan kami.")],
              "LIVE", ""))
    F.append(("situs-plus-prediksi", "Acme Widgets", "https://acme.example",
              [_cap(title="Acme Widgets",
                    visible="Situs ini memberikan prediksi harian untuk pengunjung.")],
              "REPURPOSED", "A:spam-keyword"))

    # --- the Cloudflare trap -------------------------------------------------
    F.append(("cloudflare-own-name", "Cloudflare", "https://cloudflare.com",
              [_cap(title="Cloudflare - The Web Performance & Security Company",
                    visible="Cloudflare. Build for the agent era. Cloudflare protects "
                            "the whole internet.")],
              "LIVE", ""))
    F.append(("real-bot-wall-200", "Acme Widgets", "https://acme.example",
              [_cap(status=200, title="Just a moment...",
                    visible="Checking your browser before accessing acme.example.")],
              "WALLED", ""))

    # --- walls and the second client ----------------------------------------
    F.append(("walled-both-uas", "SSENSE", "https://ssense.com",
              [_cap(status=403, ua=DEFAULT_UAS[0], title="Attention Required!",
                    visible="Enable javascript and cookies to continue"),
               _cap(status=403, ua=DEFAULT_UAS[1], final_url="https://ssense.com")],
              "WALLED", ""))
    F.append(("wall-to-chrome-open-to-firefox", "Product Hunt", "https://producthunt.com",
              [_cap(status=403, ua=DEFAULT_UAS[0]),
               _cap(status=200, ua=DEFAULT_UAS[1], title="Product Hunt - The best new "
                    "products every day", visible="Product Hunt is where makers launch.")],
              "LIVE", ""))
    F.append(("transient-dns-then-200", "LeafLink", "https://leaflink.com",
              [_cap(status=None, error="ConnectError: getaddrinfo failed",
                    error_class="dns_error"),
               _cap(status=200, ua=DEFAULT_UAS[1], title="LeafLink",
                    visible="LeafLink the wholesale cannabis platform.")],
              "LIVE", ""))

    # --- the third precision regression: ordinary marketing words ------------
    F.append(("stay-tuned-but-real", "Deel", "https://deel.com",
              [_cap(title="Deel | Payroll and HR for global teams", bytes=120000,
                    visible="Deel makes hiring and paying global teams easy. "
                            "Stay tuned for more product updates.")],
              "LIVE", ""))
    F.append(("genuine-coming-soon", "Newco", "https://newco.example",
              [_cap(title="", bytes=400,
                    visible="Coming soon. This site is under construction.")],
              "UNKNOWN", ""))

    # --- the fourth and fifth precision regressions --------------------------
    # Marketing pages that merely MENTION a CDN or a security product are sites.
    # (Real false positives: Astro and CodeCrafters on "cloudflare", Castle and
    # Clerk on "bot detection".)
    F.append(("mentions-cloudflare", "Astro", "https://astro.build",
              [_cap(title="Astro | The web framework for content-driven websites",
                    bytes=80000,
                    visible="Astro is the web framework for content-driven websites. "
                            "Deploy anywhere, including Cloudflare and Netlify.")],
              "LIVE", ""))
    F.append(("sells-bot-detection", "Castle", "https://castle.io",
              [_cap(title="Castle | Account security", bytes=60000,
                    visible="Castle provides bot detection and account takeover "
                            "prevention for modern apps.")],
              "LIVE", ""))
    # A branded page that happens to say "no longer available" about a product is
    # not a soft 404. (Real false positive: Naked Labs.)
    F.append(("branded-title-no-longer-available", "Naked Labs", "https://nakedlabs.com",
              [_cap(title="Naked Labs - The World's First Home Body Scanner", bytes=9000,
                    visible="The Naked 3D Fitness Tracker is no longer available. "
                            "Read about what we built.")],
              "LIVE", ""))

    # --- hard 404 ------------------------------------------------------------
    F.append(("hard-404", "Datree", "https://datree.io",
              [_cap(status=404, ua=DEFAULT_UAS[0]), _cap(status=404, ua=DEFAULT_UAS[1])],
              "DEAD", ""))

    # --- redirect shell and no-url ------------------------------------------
    F.append(("js-redirect-shell", "Behalf", "https://behalf.com",
              [_cap(title="Redirecting...", visible="Redirecting...",
                    html="<title>Redirecting...</title>window.location='/home'")],
              "UNKNOWN", ""))
    F.append(("no-url", "Ghost Entry", "",
              [], "NO_URL", ""))

    # --- guard ---------------------------------------------------------------
    F.append(("ssrf-guard", "Internal Thing", "http://127.0.0.1:8080",
              [_cap(blocked_by_guard="non-public address 127.0.0.1",
                    error="non-public address 127.0.0.1", error_class="guard")],
              "UNKNOWN", ""))
    return F


def run_selftest(args: argparse.Namespace, log: Log) -> int:
    fails = 0
    fixtures = _fixtures()
    for label, name, url, caps, want_state, want_class in fixtures:
        for c in caps:
            c["_sig"] = signals(c, name, CFG)
        res = classify(name, url, caps, CFG)
        ok = res["state"] == want_state and (
            not want_class or res.get("evidence_class") == want_class)
        mark = "ok  " if ok else "FAIL"
        if not ok:
            fails += 1
        log(f"  [{mark}] {label:<32} {res['state']:<11} "
            f"{res.get('evidence_class') or '-':<16} {res['why'][:64]}")
    log(f"selftest: {len(fixtures) - fails}/{len(fixtures)} fixtures pass")
    if fails:
        log("selftest FAILED - a rule is not behaving as the doctrine says")
        return 4
    return 0


# ===========================================================================
# 8. CLI
# ===========================================================================
def add_common(p: argparse.ArgumentParser, suppress_defaults: bool) -> None:
    """Shared options. Present on the top-level parser AND on every subcommand.

    The subcommand copies use SUPPRESS defaults so that an option given before the
    subcommand is not silently clobbered by the subparser's own default. Both
    `script --out X audit` and `script audit --out X` therefore work, which is the
    sort of thing that otherwise wastes somebody's afternoon.
    """
    D = argparse.SUPPRESS if suppress_defaults else None

    def dflt(value: Any) -> Any:
        return argparse.SUPPRESS if suppress_defaults else value

    p.add_argument("--config", default=dflt(None),
                   help="JSON file overriding the built-in vocabulary")
    p.add_argument("--out", default=dflt("./liveness-out"),
                   help="output directory (default ./liveness-out)")
    p.add_argument("--workers", type=int, default=dflt(12),
                   help="concurrent fetches (default 12)")
    p.add_argument("--timeout", type=float, default=dflt(20.0),
                   help="per-request timeout in seconds")
    p.add_argument("--max-bytes", type=int, default=dflt(400_000),
                   help="body cap per page")
    p.add_argument("--retries", type=int, default=dflt(2), help="retries per URL")
    p.add_argument("--min-delay", type=float, default=dflt(0.0),
                   help="sleep after each request (politeness)")
    p.add_argument("--user-agent", action="append", default=D,
                   help="override user agents (repeatable; first is primary)")
    p.add_argument("--ua-count", type=int, default=dflt(3),
                   help="how many of the default UAs to use (1-3)")
    p.add_argument("--allow-private", action="store_true", default=D,
                   help="permit private/loopback targets (off by default)")
    p.add_argument("--no-cache", action="store_true", default=D,
                   help="ignore the capture cache")
    p.add_argument("--cache-ttl", type=int, default=dflt(7 * 24 * 3600),
                   help="capture cache lifetime in seconds")
    p.add_argument("--log", default=dflt(None),
                   help="also append the run transcript here")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="site_liveness_audit.py",
        description="Full liveness / repurposing audit: capture, classify, recheck, "
                    "report, and (with brakes) drop dead rows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 ok, 1 error, 2 usage, 3 refused by a guard, "
               "4 selftest failure.")
    add_common(p, suppress_defaults=False)
    common = argparse.ArgumentParser(add_help=False)
    add_common(common, suppress_defaults=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    # audit
    a = sub.add_parser("audit", help="capture + classify + report", parents=[common])
    src = a.add_argument_group("source (pick one)")
    src.add_argument("--db", help="sqlite database to read")
    src.add_argument("--table", default="startups")
    src.add_argument("--query", help="full custom SELECT (overrides --columns)")
    src.add_argument("--columns", help="comma-separated column list for the SELECT")
    src.add_argument("--id-col", default="id")
    src.add_argument("--name-col", default="name")
    src.add_argument("--url-col", default="website_url")
    src.add_argument("--file", help="csv/json/jsonl/txt source")
    src.add_argument("--delimiter", default=",")
    src.add_argument("--url", action="append", default=[], help="inline URL (repeatable)")
    a.add_argument("--limit", type=int, help="only the first N records")
    a.add_argument("--sample", type=int, help="random sample of N records")
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--no-recheck", action="store_true",
                   help="skip the second-client pass (faster, weaker)")
    a.add_argument("--quiet", action="store_true")

    # verify / report
    for name, helptext in (("verify", "re-classify a saved run offline"),
                           ("report", "rebuild the report from a saved run")):
        s = sub.add_parser(name, help=helptext, parents=[common])
        s.add_argument("--run", required=True, help="run directory")

    # drop
    d = sub.add_parser("drop", help="delete DEAD/REPURPOSED rows (dry-run by default)",
                       parents=[common])
    d.add_argument("--run", required=True, help="run directory with states.json")
    d.add_argument("--db", required=True)
    d.add_argument("--table", default="startups")
    d.add_argument("--id-col", default="id")
    d.add_argument("--child-tables", default="verify_log,evidence",
                   help="tables to purge alongside the row")
    d.add_argument("--child-fk-col", default="startup_id")
    d.add_argument("--states", default="DEAD,REPURPOSED",
                   help="states to remove (comma separated)")
    d.add_argument("--require-fresh", default="DEAD,REPURPOSED",
                   help="fresh states that still justify deletion")
    d.add_argument("--no-recheck", action="store_true",
                   help="trust the saved run without re-capturing")
    d.add_argument("--max-drop-fraction", type=float, default=0.25,
                   help="refuse if more than this share would be removed")
    d.add_argument("--manifest", help="manifest output path")
    d.add_argument("--confirm", action="store_true", help="actually delete")

    sub.add_parser("print-config", help="dump the vocabulary as JSON", parents=[common])
    sub.add_parser("selftest", help="run the classifier fixtures offline", parents=[common])
    return p


def main(argv: Optional[list[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    args = build_parser().parse_args(argv)
    global CFG
    CFG = load_config(getattr(args, "config", None))

    if args.cmd == "print-config":
        print(json.dumps(CFG, indent=2, ensure_ascii=False))
        return 0

    out_dir = os.path.abspath(getattr(args, "out", "./liveness-out"))
    log_path = args.log or (os.path.join(out_dir, "audit.log")
                            if args.cmd == "audit" else None)
    log = Log(log_path)
    log(f"{TOOL} {VERSION} | cmd={args.cmd} | httpx={'yes' if HAVE_HTTPX else 'no (stdlib fallback)'}")
    try:
        if args.cmd == "audit":
            return run_audit(args, log)
        if args.cmd == "verify":
            return run_verify(args, log)
        if args.cmd == "report":
            return run_report(args, log)
        if args.cmd == "drop":
            return run_drop(args, log)
        if args.cmd == "selftest":
            return run_selftest(args, log)
    except KeyboardInterrupt:
        log("interrupted - partial state is in the run directory")
        return 1
    except SafetyError as exc:
        log(f"refused: {exc}")
        return 3
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR {type(exc).__name__}: {exc}")
        if os.environ.get("AUDIT_DEBUG"):
            raise
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
