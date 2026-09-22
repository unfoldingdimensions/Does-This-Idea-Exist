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

10. One host, one conversation.
   A worker pool pointed at a corpus where one host appears many times would
   hammer it concurrently - hostile crawling, and ban risk against the sources
   we depend on. The HostGate (liveness_rules.py) spaces requests per
   registrable domain, caps per-host concurrency, reads robots.txt once per
   host (RFC 9309: no robots -> allowed; 4xx -> allowed; 5xx/429 -> disallowed
   for the run, conservative), and grows a host's interval when it pushes back
   (429/403). Defaults on; --per-host-delay 0 --ignore-robots is the rollback.
   Volume never outranks being welcome back tomorrow.

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

  # settle rows the HTTP pass could not, with the machine's own Chrome
  # (writes states-merged.json; drop prefers it automatically; needs
  #  `cd scripts/render && npm install` once - puppeteer-core, no browser
  #  downloads; Chrome found via --chrome or CHROME_PATH)
  python site_liveness_audit.py render --run ./audit-out/liveness-2026-09-18-2010

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

# The vocabulary and the classifier are ONE canonical rule set. The CANONICAL
# copy lives in the app package: backend/app/liveness_rules.py (the deployable
# unit must carry its own rules - the container image ships `app/` and nothing
# else). This CLI is the guest: run from a repo checkout, `scripts/` sits beside
# `backend/`, so resolve the app package by path and import the same module the
# backend imports. Capture stays here; deciding lives there. `selftest` pins the
# shared module with its fixtures.
import importlib.util as _ilu
import pathlib as _plp


def _load_liveness_rules():
    here = _plp.Path(__file__).resolve().parent
    for candidate in (here.parent / "backend" / "app" / "liveness_rules.py",
                      here / "liveness_rules.py"):  # legacy spot, belt and braces
        if candidate.is_file():
            spec = _ilu.spec_from_file_location("liveness_rules", candidate)
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(
        "liveness_rules.py not found (looked beside the repo: "
        "<repo>/backend/app/liveness_rules.py and scripts/liveness_rules.py)")


LR = _load_liveness_rules()
liveness_rules = LR

# Names the CLI body references directly, bound from the shared module:
COMPANY = LR.COMPANY
DEFAULT_CONFIG = LR.DEFAULT_CONFIG
H1_RE = LR.H1_RE
JS_LOC_RE = LR.JS_LOC_RE
META_DESC_RE = LR.META_DESC_RE
META_REFRESH_RE = LR.META_REFRESH_RE
NOT_COMPANY = LR.NOT_COMPANY
REVIEW_GATE = LR.REVIEW_GATE
TITLE_RE = LR.TITLE_RE
UNVERIFIED = LR.UNVERIFIED
HostGate = LR.HostGate
classify = LR.classify
company_gate = LR.company_gate
decode_body = LR.decode_body
first_match = LR.first_match
host_of = LR.host_of
load_config = LR.load_config
regdom = LR.regdom
signals = LR.signals
verdict_of = LR.verdict_of
visible_text = LR.visible_text

from typing import Any, Iterable, Optional
from urllib.parse import urlparse, urljoin

VERSION = "1.1.0"
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
import urllib.robotparser


# ===========================================================================
# 1. Vocabulary -> backend/app/liveness_rules.py
#
#    The vocabulary, the signal rules and the classifier moved to
#    liveness_rules.py (2026-09-19) so the backend can consult the SAME rules
#    the CLI self-tests. `--config` still overrides the built-in vocabulary
#    through load_config, imported above. CFG below is this process's copy.
# ===========================================================================
CFG: dict[str, Any] = {}


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
    # --- politeness (doctrine 10) -------------------------------------------
    per_host_delay: float = 0.0        # min seconds between starts to one host
    per_host_concurrency: int = 1      # max in-flight requests to one host
    respect_robots: bool = True        # RFC 9309; the gate fetches robots once


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
# 4. Signal extraction + classification -> backend/app/liveness_rules.py
#
#    signals / classify / company_gate / verdict_of and the verdict constants
#    moved to liveness_rules.py (2026-09-19) and are imported above. They are
#    pure functions over capture dicts - nothing here needed the network.
# ===========================================================================


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
def _make_gate(hcfg: HttpCfg) -> Optional[HostGate]:
    """Build the politeness gate from an HttpCfg, or None when the operator
    disabled it entirely (the documented rollback: --per-host-delay 0 plus
    --ignore-robots; a bare delay of 0 still caps concurrency and reads robots)."""
    if hcfg.per_host_delay <= 0 and not hcfg.respect_robots \
            and hcfg.per_host_concurrency >= 512:
        return None
    return HostGate(delay=hcfg.per_host_delay,
                    concurrency=hcfg.per_host_concurrency,
                    respect_robots=hcfg.respect_robots,
                    robot_fetcher=(_robot_fetcher_factory(hcfg)
                                   if hcfg.respect_robots else None))


def _robot_fetcher_factory(hcfg: HttpCfg):
    """One robots.txt read per host, cached by the gate (RFC 9309). Returns a
    parser, or None when there is nothing to enforce: no robots -> allowed,
    4xx -> allowed (no policy published), 5xx/429 -> DISALLOWED for the run
    (conservative - the server is already pushing back), network error ->
    allowed (we could not know)."""
    def fetch_robots(host: str):
        for scheme in ("https", "http"):
            try:
                cap = fetch_once(f"{scheme}://{host}/robots.txt",
                                 DEFAULT_UAS[0],
                                 HttpCfg(timeout=6.0, retries=0,
                                         max_bytes=200_000,
                                         allow_private=hcfg.allow_private))
            except Exception:  # noqa: BLE001
                continue
            st = cap.get("status")
            if st == 200:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse((cap.get("html") or "").splitlines())
                return rp
            if st in (403, 429) or (st is not None and st >= 500):
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(["User-agent: *", "Disallow: /"])
                return rp  # the server is pushing back: disallow for this run
            if st is not None and 400 <= st < 500:
                return None  # no policy published -> allowed
            # other (redirects that ended oddly, weird statuses): try next scheme
        return None
    return fetch_robots


def _fetch_gated(url: str, ua: str, hcfg: HttpCfg,
                 gate: Optional[HostGate]) -> dict[str, Any]:
    """One fetch through the politeness gate: robots first, then a host slot.
    A robots refusal is a CAPTURE, not an exception - it classifies honestly
    as UNKNOWN ('we chose not to fetch'), never as death."""
    if gate is None:
        return fetch_once(url, ua, hcfg)
    host = regdom(host_of(url), CFG)
    if not gate.robots_allowed(url, host):
        return {"url": url, "ua": ua, "status": None, "error": "",
                "error_class": "robots",
                "robots_note": "robots.txt disallows this path (politeness gate)",
                "final_url": "", "chain": [], "content_type": "", "server": "",
                "bytes": 0, "truncated": False, "title": "",
                "meta_description": "", "h1": "", "visible": "", "html": "",
                "elapsed_ms": 0, "blocked_by_guard": ""}
    gate.reserve(host)
    try:
        cap = fetch_once(url, ua, hcfg)
    finally:
        gate.release(host)
    gate.record_result(host, cap.get("status"))
    return cap


def _spread_by_host(records: list[dict]) -> list[dict]:
    """Interleave records across hosts so the submission queue itself is
    host-spread: a worker blocked waiting for one host's slot is then rare,
    and idle workers almost always hold another host's job."""
    groups: dict[str, "collections.deque"] = {}
    for r in records:
        groups.setdefault(regdom(host_of(r["url"]), CFG),
                          collections.deque()).append(r)
    out: list[dict] = []
    queue = list(groups.values())
    while queue:
        remaining = []
        for q in queue:
            if q:
                out.append(q.popleft())
                remaining.append(q)
        queue = remaining
    return out


def capture_all(records: list[dict], hcfg: HttpCfg, uas: list[str], log: Log,
                cache: Optional["Cache"] = None,
                gate: Optional[HostGate] = None) -> None:
    """Fetch every record with the primary UA (cache-aware, resumable)."""
    todo = [r for r in records if not (cache and cache.get(r["url"], uas[0]))]
    log(f"capture: {len(records)} records, {len(todo)} to fetch, "
        f"{len(records) - len(todo)} from cache")
    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max(1, hcfg.workers)) as ex:
        futs = {ex.submit(_fetch_gated, r["url"], uas[0], hcfg, gate): r
                for r in _spread_by_host(todo)}
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
                cache: Optional["Cache"] = None,
                gate: Optional[HostGate] = None) -> None:
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
            for r in _spread_by_host(need):
                if any(c.get("ua") == alt for c in (r.get("caps") or [])):
                    continue
                cached = cache.get(r["url"], alt) if cache else None
                if cached:
                    futs[ex.submit(lambda c=cached: c)] = r
                else:
                    futs[ex.submit(_fetch_gated, r["url"], alt, hcfg, gate)] = r
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
        f"| timeout={args.timeout}s | config={LR.config_hash()}")

    hcfg = HttpCfg(timeout=args.timeout, max_bytes=args.max_bytes,
                   retries=args.retries, allow_private=args.allow_private,
                   politerelay=args.min_delay,
                   per_host_delay=args.per_host_delay,
                   per_host_concurrency=args.per_host_concurrency,
                   respect_robots=not args.ignore_robots)
    hcfg.workers = args.workers  # type: ignore[attr-defined]
    uas = args.user_agent or DEFAULT_UAS
    uas = uas[: max(1, args.ua_count)]
    gate = _make_gate(hcfg)
    if gate is not None:
        log(f"politeness: per-host delay {hcfg.per_host_delay:.2f}s, "
            f"per-host concurrency {hcfg.per_host_concurrency}, "
            f"robots {'on' if hcfg.respect_robots else 'off'}")
    cache = Cache(os.path.join(out_dir, "captures.cache.jsonl"),
                  ttl_seconds=args.cache_ttl) if not args.no_cache else None

    capture_all(records, hcfg, uas, log, cache, gate)

    # score bodies before the recheck pass so the pre-filter can work
    for r in records:
        for c in r.get("caps") or []:
            c["_sig"] = signals(c, r["name"], CFG)

    if not args.no_recheck and len(uas) > 1:
        recheck_all(records, hcfg, uas, log, cache, gate)

    # final classification over all captures
    for r in records:
        for c in r.get("caps") or []:
            if "_sig" not in c:
                c["_sig"] = signals(c, r["name"], CFG)
        r["result"] = classify(r["name"], r["url"], r.get("caps") or [], CFG)
        # the company gate judges the fullest evidence we have, and runs on the
        # same captures so a run carries both verdicts (see company_gate)
        best_cap = max(r.get("caps") or [{}],
                       key=lambda c: len(c.get("visible") or ""), default={})
        r["gate"] = company_gate(r["url"], best_cap.get("_sig") or {}, CFG)

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
        "config_hash": LR.config_hash(),
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
            "company_gate": (r.get("gate") or {}).get("verdict", ""),
            "company_gate_why": (r.get("gate") or {}).get("why", ""),
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


STATE_ORDER = ["LIVE", "DEAD", "REPURPOSED", "MOVED", "BANNED", "WALLED", "UNKNOWN",
               "NO_URL"]


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
    gate_counts = collections.Counter(s.get("company_gate") or "-" for s in states)
    not_company = [s for s in states if s.get("company_gate") == NOT_COMPANY]
    if any(gate_counts.values()):
        A("## Company gate - is this a company, or a project page?")
        A("")
        A("Runs on the same captures, before admission and before enrichment. It "
          "rejects only high-confidence non-companies (a project-hosting host, or a "
          "cluster of project/docs markers with no commercial signal). UNVERIFIED is "
          "not a queue: it means no positive evidence either way, and the admin path "
          "already handles unreadable rows.")
        A("")
        for k in (COMPANY, UNVERIFIED, NOT_COMPANY, REVIEW_GATE):
            A(f"- **{k}**: {gate_counts.get(k, 0)}")
        A("")
        if not_company:
            A(f"### Rejected as non-company ({len(not_company)})")
            A("")
            A("| # | Name | URL | Why |")
            A("|---|---|---|---|")
            for s in sorted(not_company, key=lambda x: str(x["name"]).lower()):
                A(f'| {esc(s["id"], 12)} | {esc(s["name"], 40)} | {esc(s["url"], 60)} | '
                  f'{esc(s.get("company_gate_why"), 90)} |')
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
        best_cap = max(caps, key=lambda c: len(c.get("visible") or ""), default={})
        gate = company_gate(urls.get(rid, ""), best_cap.get("_sig") or {}, CFG)
        states.append({"id": rid, "name": names.get(rid, ""), "url": urls.get(rid, ""),
                       "state": res["state"], "why": res["why"],
                       "evidence_class": res.get("evidence_class", ""),
                       "http_status": res.get("http_status"),
                       "final_url": res.get("final_url", ""), "title": res.get("title", ""),
                       "spam": res.get("spam", ""), "shell": res.get("shell", ""),
                       "stored_host": res.get("stored_host", ""),
                       "final_host": res.get("final_host", ""),
                       "redirected": res.get("redirected", False),
                       "verdicts": res.get("verdicts", {}),
                       "company_gate": gate["verdict"], "company_gate_why": gate["why"]})
    states.sort(key=lambda s: (str(s["name"]).lower(), str(s["id"])))
    meta = {"tool": TOOL, "version": VERSION, "generated_at": now(), "source": run_dir,
            "config_hash": LR.config_hash()}
    # A merged state file is EVIDENCE - the render pass's per-row receipts that a
    # drop may trust (--no-recheck). A re-verify over it must not clobber that
    # with HTTP-only states, so it writes alongside instead.
    # (Footgun found by the 2026-09-19 critique, F2.)
    merged_path = os.path.join(run_dir, "states-merged.json")
    out_name = "states.json"
    if os.path.exists(merged_path):
        out_name = "states-reverified.json"
        log("note: states-merged.json exists (a render pass ran); writing "
            "states-reverified.json so the merged evidence survives")
    atomic_write(os.path.join(run_dir, out_name),
                 json.dumps(states, indent=1, ensure_ascii=False))
    write_report(run_dir, states, meta, log)
    counts = collections.Counter(s["state"] for s in states)
    log("reverified: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER))
    return 0


def run_report(args: argparse.Namespace, log: Log) -> int:
    run_dir = os.path.abspath(args.run)
    states = json.load(open(os.path.join(run_dir, "states.json"), encoding="utf-8"))
    meta = {"tool": TOOL, "version": VERSION, "generated_at": now(), "source": run_dir,
            "config_hash": LR.config_hash()}
    try:
        meta.update(json.load(open(os.path.join(run_dir, "run.json"), encoding="utf-8")))
    except Exception:  # noqa: BLE001
        pass
    write_report(run_dir, states, meta, log)
    return 0


def find_chrome(explicit: Optional[str]) -> str:
    """Locate a Chrome/Chromium for the renderer. The machine's own browser
    renders; nothing is downloaded."""
    if explicit:
        return explicit
    env = os.environ.get("CHROME_PATH")
    if env and os.path.isfile(env):
        return env
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     r"Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium",
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return ""


def run_render(args: argparse.Namespace, log: Log) -> int:
    """Settle rows the HTTP pass could not, with a real browser.

    Round 4 of the 2026-09-18 audit did this by hand from a vendored copy and
    settled 16 of 18 UNKNOWNs - and the drop that followed TRUSTED its output
    (--states-file). A stage that feeds a destructive decision must be
    reproducible from the repo, so here it is: render every selected row with
    the machine's Chrome (scripts/render/render.mjs, puppeteer-core, no browser
    downloads), judge the rendered capture with the SAME rules as the HTTP
    pass, and write states-merged.json - the file `drop` now prefers
    automatically and `verify` refuses to clobber.

    Selection defaults to the ambiguity classes (UNKNOWN / WALLED / MOVED):
    DEAD and REPURPOSED are already decided by content evidence on a 200 body,
    and re-judging them would only add churn.
    """
    import subprocess

    run_dir = os.path.abspath(args.run)
    states_path = os.path.join(run_dir, "states.json")
    if not os.path.isfile(states_path):
        log(f"no states.json under {run_dir}")
        return 2
    with open(states_path, encoding="utf-8") as fh:
        states = json.load(fh)
    if not states:
        log("nothing to render")
        return 0

    chrome = find_chrome(args.chrome)
    if not chrome:
        log("Chrome not found - pass --chrome or set CHROME_PATH")
        return 2
    node = shutil.which("node")
    if not node:
        log("node is not on PATH - the renderer needs it (Node >= 23)")
        return 2
    if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "render", "node_modules")):
        log("puppeteer-core is not installed: cd scripts/render && npm install")
        return 2

    # rebuild the HTTP captures so the merged classification has both bodies
    caps_by_id: dict[Any, list[dict]] = collections.defaultdict(list)
    caps_path = os.path.join(run_dir, "captures.jsonl")
    if os.path.isfile(caps_path):
        with open(caps_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                caps_by_id[c.get("_record_id")].append(c)

    want = {s.strip().upper() for s in args.states.split(",") if s.strip()}
    targets = [s for s in states if s.get("state", "") in want]
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        counts = collections.Counter(s.get("state") for s in states)
        log(f"nothing to render among states={sorted(want)} "
            f"(run holds: {dict(counts)})")
        return 0

    merged_path = os.path.join(run_dir, "states-merged.json")
    if os.path.exists(merged_path):
        bak = f"{merged_path}.bak-{stamp()}"
        shutil.copy2(merged_path, bak)
        log(f"existing merged file backed up: {os.path.basename(bak)}")

    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render")
    jobs_path = os.path.join(run_dir, "render-jobs.json")
    results_path = os.path.join(run_dir, "render-results.jsonl")
    # The renderer is a second fetch surface and inherits the politeness gate
    # (doctrine 10): robots checked here, and each job carries the gap it must
    # wait before its goto, computed on that host's schedule (renders run
    # sequentially in node, so per-job waits compose into intervals).
    hcfg = HttpCfg(timeout=args.timeout, max_bytes=args.max_bytes, retries=0,
                   allow_private=args.allow_private,
                   per_host_delay=args.per_host_delay,
                   per_host_concurrency=args.per_host_concurrency,
                   respect_robots=not args.ignore_robots)
    gate = _make_gate(hcfg)
    jobs: list[dict] = []
    for s in targets:
        if gate is not None:
            host = regdom(host_of(s.get("url", "")), CFG)
            if not gate.robots_allowed(s.get("url", ""), host):
                s["render_skipped"] = "robots.txt disallows this path"
                log(f"  skipped {s['id']:>6} {str(s.get('name'))[:26]!r}: robots.txt")
                continue
            wait_ms = int(max(0.0, gate.next_slot(host) - time.monotonic()) * 1000)
        else:
            wait_ms = 0
        jobs.append({"id": s["id"], "url": s["url"], "waitMs": wait_ms})

    renders: dict[Any, dict] = {}
    if jobs:
        atomic_write(jobs_path, json.dumps({
            "chromePath": chrome,
            "timeoutMs": int(args.timeout * 1000),
            "waitMs": args.wait_ms,
            "maxChars": args.max_bytes,
            "jobs": jobs,
        }, indent=1))
        log(f"render: {len(jobs)} of {len(targets)} selected rows via "
            f"{os.path.basename(chrome)} (timeout {args.timeout:.0f}s, "
            f"settle {args.wait_ms}ms)")
        proc = subprocess.run([node, "render.mjs", jobs_path, results_path],
                              cwd=scripts_dir, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        for line in (proc.stderr or "").splitlines():
            if line.strip():
                log(f"  {line.strip()}")
        if proc.returncode != 0:
            log(f"renderer failed (exit {proc.returncode}): {(proc.stdout or '')[:200]}")
            return 1

        with open(results_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    renders[r.get("id")] = r

    outcomes = {"unchanged": 0, "changed": 0, "failed": 0}
    merged_rows: list[dict] = []
    for s in states:
        row = dict(s)
        r = renders.get(s.get("id"))
        if s.get("state", "") not in want or r is None:
            row.setdefault("evidence_mode", "http")
            merged_rows.append(row)
            continue
        # the rendered capture, in the same shape as an HTTP capture, so the
        # SAME rules judge it (one classifier, two clients)
        cap = {
            "url": s.get("url", ""), "ua": "render", "status": r.get("status"),
            "error": r.get("error") or "",
            "error_class": classify_error(r.get("error") or "") if r.get("error") else "",
            "final_url": r.get("final_url") or "", "chain": [],
            "content_type": "text/html", "server": "",
            "bytes": len(r.get("html") or "") or len(r.get("visible") or ""),
            "truncated": False, "title": r.get("title") or "",
            "meta_description": "", "h1": r.get("h1") or "",
            "visible": r.get("visible") or "", "html": r.get("html") or "",
            "elapsed_ms": 0, "blocked_by_guard": "",
        }
        caps = [dict(c) for c in caps_by_id.get(s.get("id")) or []]
        if r.get("ok"):
            caps.append(cap)
        else:
            outcomes["failed"] += 1
            log(f"  render failed {s['id']:>6} {str(s.get('name'))[:26]!r}: "
                f"{(r.get('error') or '')[:90]}")
        for c in caps:
            if "_sig" not in c:
                c["_sig"] = signals(c, s.get("name", ""), CFG)
        res = classify(s.get("name", ""), s.get("url", ""), caps, CFG)
        best_cap = max(caps, key=lambda c: len(c.get("visible") or ""), default={})
        gate = company_gate(s.get("url", ""), best_cap.get("_sig") or {}, CFG)
        row.update({
            "state": res["state"], "why": res["why"],
            "evidence_class": res.get("evidence_class", ""),
            "http_status": res.get("http_status"),
            "final_url": res.get("final_url", ""),
            "title": res.get("title", ""), "spam": res.get("spam", ""),
            "shell": res.get("shell", ""),
            "stored_host": res.get("stored_host", ""),
            "final_host": res.get("final_host", ""),
            "redirected": res.get("redirected", False),
            "verdicts": res.get("verdicts", {}),
            "company_gate": gate["verdict"], "company_gate_why": gate["why"],
            # the pre-render verdict and the render receipt travel with the row:
            # a drop that trusts this file (--no-recheck) then carries a manifest
            # that says WHY each row went, including what the browser saw
            "http_state": s.get("state", ""), "http_why": s.get("why", ""),
            "evidence_mode": "http+render" if r.get("ok") else "http",
            "browser_evidence": {**{k: r.get(k) for k in
                                    ("status", "final_url", "title", "h1",
                                     "rendered_at") if r.get(k) is not None},
                                 "visible_sample": (r.get("visible") or "")[:400]},
        })
        if res.get("state") == "MOVED":
            row["moved_domain"] = res.get("final_host", "")
        if r.get("ok"):
            if res["state"] != s.get("state"):
                outcomes["changed"] += 1
                log(f"  {s['id']:>6} {str(s.get('name'))[:26]:<26} "
                    f"{s.get('state'):<8} -> {res['state']:<8} {res['why'][:60]}")
            else:
                outcomes["unchanged"] += 1
        merged_rows.append(row)

    merged_rows.sort(key=lambda s: (str(s["name"]).lower(), str(s["id"])))
    atomic_write(merged_path,
                 json.dumps(merged_rows, indent=1, ensure_ascii=False))
    counts = collections.Counter(s["state"] for s in merged_rows)
    log(f"merged: {merged_path}")
    log("merged states: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER))
    log("render outcomes: "
        + ", ".join(f"{k}={outcomes[k]}" for k in ("unchanged", "changed", "failed")))
    return 0


def run_drop(args: argparse.Namespace, log: Log) -> int:
    """Delete DEAD/REPURPOSED rows - with a receipt and a set of brakes."""
    if not args.db:
        log("drop requires --db")
        return 2
    run_dir = os.path.abspath(args.run)
    # An explicit --states-file wins. Otherwise the merged file (a render pass
    # ran) is the better basis: its rows carry the rendered evidence and the
    # pre-render verdicts. No manual join - this is the Round-5 lesson fixed.
    if args.states_file:
        states_path = os.path.abspath(args.states_file)
    else:
        merged = os.path.join(run_dir, "states-merged.json")
        if os.path.exists(merged):
            states_path = os.path.abspath(merged)
            log("states file: states-merged.json (the render pass ran; its "
                "evidence is the basis). Rows only visible to a renderer will "
                "fail a fresh HTTP recheck - use --no-recheck to trust the "
                "merged evidence, which the manifest then embeds.")
        else:
            states_path = os.path.join(run_dir, "states.json")
    states = json.load(open(states_path, encoding="utf-8"))
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
                   allow_private=args.allow_private,
                   per_host_delay=args.per_host_delay,
                   per_host_concurrency=args.per_host_concurrency,
                   respect_robots=not args.ignore_robots)
    hcfg.workers = args.workers  # type: ignore[attr-defined]
    uas = (args.user_agent or DEFAULT_UAS)[: max(1, args.ua_count)]
    gate = _make_gate(hcfg)

    # 1. fresh evidence at drop time (doctrine 8)
    if not args.no_recheck:
        log("re-capturing fresh evidence before deleting")
    else:
        log("WARNING: --no-recheck - trusting the evidence recorded in "
            f"{os.path.relpath(states_path)} without re-capturing it. The manifest "
            "will carry whatever that file recorded per row.")
    if not args.no_recheck:
        for s in targets:
            caps = []
            with cf.ThreadPoolExecutor(max_workers=min(4, len(uas) or 1)) as ex:
                futs = [ex.submit(_fetch_gated, s["url"], ua, hcfg, gate)
                        for ua in uas]
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
        "tool": f"{TOOL} {VERSION}", "config_hash": LR.config_hash(),
        "run": run_dir, "db": os.path.abspath(args.db), "table": table,
        "states_dropped": args.states or "DEAD,REPURPOSED",
        "states_file": states_path,
        "evidence_mode": ("trusted-run (no re-capture)" if args.no_recheck
                          else "fresh re-capture at drop time"),
        "instruction": "Rows a prior run filed DEAD/REPURPOSED. Fresh evidence was "
                       "re-captured at drop time unless --no-recheck. Child-table "
                       "history is included below.",
        "db_backup": os.path.basename(backup) if args.confirm else None,
        "rows": [{**present.get(s["id"], {}), "_state": s["state"], "_why": s["why"],
                  "_fresh_state": s.get("fresh_state"),
                  "_fresh_why": s.get("fresh_why"),
                  "_evidence_class": s.get("fresh_evidence_class") or s.get("evidence_class"),
                  "_url": s["url"], "_name": s["name"],
                  # whatever the run recorded for this row, including rendered
                  # (browser) evidence when the row was only visible to a renderer
                  "_run_evidence": {k: s.get(k) for k in
                                    ("source", "http_state", "http_why", "state", "why",
                                     "evidence_class", "title", "final_url", "spam", "shell",
                                     "browser_evidence", "verdicts", "moved_domain")
                                    if s.get(k) is not None},
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
# 7b. Sampled QA (Sequence 4, docs/liveness-funnel-plan.md) - auto-approval is
# only legitimate once its error rate is MEASURED, and a breach stops the line.
# ===========================================================================
# The budget is configuration, not law of nature: a breach refuses the import
# (the safe direction) unless the operator overrides explicitly, and the
# override is logged on the import receipt.
QA_BUDGET = 0.005  # <0.5% false-approval rate (docs/scale-to-10000-plan.md §6)
QA_SAMPLE_RATE = 0.02  # 2% of the LIVE slice
QA_SAMPLE_FLOOR = 30  # ...but never fewer than 30 LIVE rows in the worksheet
# Worksheet states, in priority order: everything suspicious is sampled IN
# FULL; only the clean majority is sampled at the rate above.
QA_FULL_STATES = ("DEAD", "REPURPOSED", "MOVED", "BANNED")
QA_WALL_STATES = ("WALLED", "UNKNOWN")
QA_VERDICTS = ("approve", "reject", "unsure")


def _qa_load_states(run_dir: str, log: Log) -> tuple[list[dict], str]:
    """Load the run's state rows - the merged file when a render pass ran.

    Mirrors the import/drop preference: rendered evidence is the better basis
    for a verdict worksheet, so the sample must include the rows only the
    browser could settle.
    """
    merged = os.path.join(run_dir, "states-merged.json")
    plain = os.path.join(run_dir, "states.json")
    path = merged if os.path.isfile(merged) else plain
    if not os.path.isfile(path):
        raise SafetyError(f"no states file under {run_dir} - run an audit first")
    with open(path, encoding="utf-8") as fh:
        states = json.load(fh)
    if not isinstance(states, list) or not states:
        raise SafetyError(f"{path} holds no rows")
    log(f"qa sample basis: {os.path.basename(path)} ({len(states)} rows)")
    return states, path


def _qa_sample(states: list[dict], seed: int,
               rate: float = QA_SAMPLE_RATE, floor: int = QA_SAMPLE_FLOOR
               ) -> tuple[list[dict], dict[str, int]]:
    """Deterministic stratified sample. Same seed -> the same worksheet.

    Strata: every DEAD/REPURPOSED/MOVED/BANNED row (a wrong kill verdict is
    the expensive kind), every WALLED/UNKNOWN row (the gate could not see the
    site), then a seeded random slice of LIVE big enough to measure the
    false-approval rate (default 2%, floor 30). The LIVE draw uses
    random.Random(seed) over rows sorted by (name, id) so the sample is a
    function of the run and the seed alone - never of dict or file order.
    """
    by_state: dict[str, list[dict]] = collections.defaultdict(list)
    for s in states:
        by_state[str(s.get("state", "")).upper()].append(s)
    picked: list[dict] = []
    for state in (*QA_FULL_STATES, *QA_WALL_STATES):
        picked.extend(by_state.get(state, ()))
    live = sorted(by_state.get("LIVE", ()),
                  key=lambda s: (str(s.get("name", "")).lower(), str(s.get("id", ""))))
    rng = random.Random(seed)
    n_live = max(floor, round(len(live) * rate)) if live else 0
    picked.extend(rng.sample(live, min(n_live, len(live))))
    counts = {k: len(by_state[k]) for k in by_state}
    # de-dupe by id, keep worksheet order stable (state strata first, then name)
    seen: set = set()
    uniq: list[dict] = []
    for s in sorted(picked, key=lambda s: (str(s.get("name", "")).lower(),
                                           str(s.get("id", "")))):
        key = (str(s.get("id")), str(s.get("state", "")).upper())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    return uniq, counts


def _qa_worksheet(run_dir: str, rows: list[dict], seed: int,
                  basis: str, counts: dict[str, int], log: Log) -> dict:
    """Write qa-worksheet.md + qa-worksheet.csv: one row per sampled entry,
    each carrying its evidence and an empty verdict column to fill."""
    ts = dt.datetime.now().isoformat(timespec="seconds")
    for s in rows:
        s["_kind"] = ("kill-strata" if str(s.get("state", "")).upper() in QA_FULL_STATES
                      else "wall-strata" if str(s.get("state", "")).upper() in QA_WALL_STATES
                      else "live-sample")
    lines = [
        "# QA worksheet", "",
        f"- run: `{os.path.basename(run_dir)}`",
        f"- basis: `{os.path.basename(basis)}`",
        f"- seed: `{seed}` (same seed -> the same sample)",
        f"- sampled: {len(rows)} of {sum(counts.values())} rows "
        f"(full strata: {'/'.join(QA_FULL_STATES)} + {'/'.join(QA_WALL_STATES)}; "
        f"LIVE at {QA_SAMPLE_RATE:.0%}, floor {QA_SAMPLE_FLOOR})",
        f"- run state counts: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        f"- generated: {ts}", "",
        "Fill `verdict` in the CSV with one of: " + ", ".join(QA_VERDICTS) +
        ". `reject` on a LIVE-sampled row means the funnel admitted a site it "
        "should not have - that is a false approval and counts against the "
        "budget in qa-result.json.", "",
    ]
    with open(os.path.join(run_dir, "qa-worksheet.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "url", "state", "why", "kind", "verdict", "qa_note"])
        for s in rows:
            w.writerow([s.get("id", ""), s.get("name", ""), s.get("url", ""),
                        s.get("state", ""), (s.get("why") or "")[:200],
                        s.get("_kind", ""), "", ""])
            why = (s.get("why") or "").replace("|", "\\|")
            gate = s.get("company_gate", "")
            lines.append(
                f"| {s.get('id', '')} | {s.get('name', '')} | {s.get('state', '')} "
                f"| {gate} | {why[:140]} | {s.get('_kind', '')} | |")
    lines.insert(0, "")
    lines.insert(0, "| id | name | state | gate | why | kind | verdict |")
    lines.insert(0, "|---|---|---|---|---|---|---|")
    atomic_write(os.path.join(run_dir, "qa-worksheet.md"), "\n".join(lines) + "\n")
    log(f"qa worksheet: {len(rows)} rows -> qa-worksheet.md / qa-worksheet.csv "
        f"(fill verdict, then `qa --run {run_dir} --record`)")
    return {"sampled": len(rows), "seed": seed, "basis": os.path.basename(basis),
            "counts": counts}


def run_qa(args: argparse.Namespace, log: Log) -> int:
    """Sample a run into a QA worksheet, or record completed verdicts."""
    if getattr(args, "record", False) and getattr(args, "sweep", False):
        raise SafetyError("qa --record and qa --sweep are separate operations")
    if getattr(args, "sweep", False):
        return _qa_sweep(args, log)
    run = getattr(args, "run", None)
    if not run:
        raise SafetyError("qa needs --run (a run directory) or --sweep")
    run_dir = os.path.abspath(run)
    if not os.path.isdir(run_dir):
        raise SafetyError(f"no such run directory: {run_dir}")
    if args.record:
        return _qa_record(run_dir, args, log)
    states, basis = _qa_load_states(run_dir, log)
    rows, counts = _qa_sample(states, args.seed, rate=args.rate, floor=args.floor)
    if not rows:
        log("nothing to sample: the run has no rows in any QA stratum")
        return 1
    _qa_worksheet(run_dir, rows, args.seed, basis, counts, log)
    return 0


def _qa_ledger(out_root: str, entry: dict) -> None:
    """QA rounds ledger - append-only, one JSON object per line.

    Every recorded round (run or sweep) lands here in order, so the error
    budget's history is a straight line, not files scattered across run dirs.
    """
    path = os.path.join(out_root, "qa-rounds.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _qa_sweep(args: argparse.Namespace, log: Log) -> int:
    """Re-sample machine-admitted rows (the weekly sweep).

    Reads the archive directly (read-only): every row the funnel admitted
    (`approval_source='machine'`) inside the window becomes the LIVE stratum
    of a fresh worksheet. The human samples it, `qa --record` scores it, and
    the rate joins the same budget as run-based rounds. This is the loop that
    catches slow rot: a rule drift that passes per-run QA but fails across a
    week of admissions.
    """
    db_path = getattr(args, "db", None)
    if not db_path:
        raise SafetyError("qa --sweep needs --db (the archive to re-sample)")
    days = int(getattr(args, "sweep_days", 7) or 7)
    uri = os.path.abspath(db_path).replace("\\", "/")
    con = sqlite3.connect(f"file:{uri}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "select id, name, website_url, approved_by, approval_note, verified_at "
            "from startups where approval_source = 'machine' and verified = 1 "
            f"and verified_at >= datetime('now', '-{days} days') "
            "order by name collate nocase, id").fetchall()
    finally:
        con.close()
    if not rows:
        log(f"qa sweep: no machine-admitted rows in the last {days} days")
        return 0
    recs = [{"id": r["id"], "name": r["name"], "url": r["website_url"],
             # they were admitted as alive; the QA question is whether that
             # admission was right, so they land in the LIVE stratum
             "state": "LIVE",
             "why": r["approval_note"] or r["approved_by"] or "",
             "company_gate": r["approved_by"] or ""} for r in rows]
    out_root = os.path.abspath(getattr(args, "out", "./liveness-out"))
    sweep_dir = os.path.join(out_root, f"qa-sweep-{stamp()}")
    os.makedirs(sweep_dir, exist_ok=True)
    atomic_write(os.path.join(sweep_dir, "run.json"), json.dumps(
        {"tool": TOOL, "version": VERSION, "kind": "qa-sweep",
         "window_days": days, "generated_at": now(), "rows": len(recs)},
        indent=2, ensure_ascii=False))
    atomic_write(os.path.join(sweep_dir, "states.json"),
                 json.dumps(recs, indent=1, ensure_ascii=False))
    sampled, counts = _qa_sample(recs, args.seed, rate=args.rate, floor=args.floor)
    _qa_worksheet(sweep_dir, sampled, args.seed,
                  os.path.join(sweep_dir, "states.json"), counts, log)
    _qa_ledger(out_root, {"kind": "sweep", "at": now(),
                          "run": os.path.basename(sweep_dir),
                          "window_days": days, "population": len(recs),
                          "sampled": len(sampled)})
    log(f"qa sweep: {len(sampled)} of {len(recs)} machine-admitted rows "
        f"(last {days} days) -> {sweep_dir}")
    return 0


def _qa_record(run_dir: str, args: argparse.Namespace, log: Log) -> int:
    """Ingest completed verdicts -> qa-result.json with the false-approval rate.

    The rate that counts against the budget is the false-approval rate:
    rejected-or-should-not-exist verdicts among the LIVE sample. Kill-strata
    verdicts do not water it down - they are recorded per-row for the rules
    feedback loop, but the budget reads only the LIVE slice, because that is
    the slice auto-approval actually published.
    """
    csv_path = os.path.join(run_dir, "qa-worksheet.csv")
    if not os.path.isfile(csv_path):
        raise SafetyError(f"no {csv_path} - run `qa` without --record first")
    verdict_tally: dict[str, int] = {v: 0 for v in QA_VERDICTS}
    live_rows: list[dict] = []
    other_rows: list[dict] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            verdict = (row.get("verdict") or "").strip().lower()
            kind = (row.get("kind") or "").strip()
            if verdict and verdict in verdict_tally:
                verdict_tally[verdict] += 1
            entry = {"id": row.get("id"), "name": row.get("name"),
                     "state": row.get("state"), "kind": kind,
                     "verdict": verdict or None,
                     "note": (row.get("qa_note") or "").strip() or None}
            if kind == "live-sample":
                live_rows.append(entry)
            else:
                other_rows.append(entry)
    if not any(e["verdict"] for e in live_rows):
        raise SafetyError(
            "no verdicts on the LIVE sample - the false-approval rate would be "
            "meaningless; fill the verdict column first")
    live_verdicted = [e for e in live_rows if e["verdict"]]
    false_approvals = [e for e in live_verdicted if e["verdict"] == "reject"]
    rate = (len(false_approvals) / len(live_verdicted)) if live_verdicted else 0.0
    result = {
        "run": os.path.basename(run_dir),
        "recorded_at": dt.datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "budget": QA_BUDGET,
        "live_sample_size": len(live_rows),
        "live_verdicted": len(live_verdicted),
        "false_approvals": len(false_approvals),
        "false_approval_rate": round(rate, 6),
        "within_budget": rate <= QA_BUDGET,
        "verdict_tally": verdict_tally,
        "live_rows": live_rows,
        "other_rows": other_rows,
    }
    atomic_write(os.path.join(run_dir, "qa-result.json"),
                 json.dumps(result, indent=2, ensure_ascii=False))
    _qa_ledger(os.path.dirname(run_dir) or ".", {
        "kind": "run", "at": result["recorded_at"],
        "run": result["run"], "seed": result["seed"],
        "live_verdicted": len(live_verdicted),
        "false_approvals": len(false_approvals),
        "rate": result["false_approval_rate"],
        "within_budget": result["within_budget"]})
    log(f"qa recorded: {len(false_approvals)}/{len(live_verdicted)} false approvals "
        f"= {rate:.2%} (budget {QA_BUDGET:.1%}) -> "
        f"{'WITHIN budget' if result['within_budget'] else 'BREACH - the import will refuse'}")
    return 0


# ===========================================================================
# 7. Selftest - the fixtures are the real cases that taught us the rules.
# ===========================================================================
def _cap(**kw: Any) -> dict[str, Any]:
    # url/final_url default to EMPTY on purpose: run_selftest fills them from the
    # fixture's own URL unless the fixture names a different one. A hardcoded
    # default here would silently assert a cross-domain move in every fixture.
    base = {"url": "", "ua": DEFAULT_UAS[0], "status": 200,
            "error": "", "error_class": "", "final_url": "",
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

    # --- the sixth, seventh and eighth precision regressions (browser pass) ---
    # A registrar lander that never says "parked" or "for sale": the HTTP body is
    # an empty shell, so only a renderer sees it. (Real: godutchpay.in, goDutch.)
    F.append(("godaddy-lander", "goDutch", "http://godutchpay.in",
              [_cap(status=200, final_url="https://godutchpay.in/lander", title="",
                    bytes=30000,
                    visible="Related Searches go dutch pay Copyright (c) 1999-2026 "
                            "GoDaddy, LLC. All rights reserved.")],
              "DEAD", ""))
    # SiteGround's captcha returns 202 with an empty body. (Real: magdrive.space.)
    F.append(("siteground-captcha", "Magdrive", "http://www.magdrive.space/",
              [_cap(status=202, title="Robot Challenge Screen", bytes=40000,
                    final_url="https://www.magdrive.space/.well-known/sgcaptcha/?r=%2F",
                    visible="magdrive.space Checking the site connection security")],
              "WALLED", ""))
    # Parked-domain monetisation redirect. (Real: behalf.com -> HeadlineLogic.)
    F.append(("monetised-redirect", "Behalf", "http://www.behalf.com",
              [_cap(status=200, bytes=60000,
                    final_url="https://headlinelogic.com/?d=behalf.com&pcid=56&brand=behalf.com",
                    title="HeadlineLogic News Portal",
                    visible="News Entertainment Weather Sports Finance Top Stories")],
              "REPURPOSED", "C:monetised-redirect"))

    # --- the render pass: same rules, two clients ----------------------------
    # The render pass appends a "render" capture to the HTTP captures and the
    # SAME classifier decides (Round 4 settled 16 of 18 UNKNOWNs this way).
    # These two pin the merge semantics: the best body - most visible text -
    # wins, whatever client produced it. (Real shape: Chaldal, a client-rendered
    # SPA that answers an empty shell to a scripted client; Run The World, whose
    # lander only exists after JS.)
    F.append(("render-settles-empty-shell", "Chaldal", "https://chaldal.example",
              [_cap(status=200, bytes=200, title="", visible=""),
               _cap(status=200, ua="render", bytes=90000,
                    title="Chaldal - Online Grocery Shop",
                    visible="Chaldal delivers groceries in Dhaka. Pricing FAQs "
                            "Contact us")],
              "LIVE", ""))
    F.append(("render-sees-the-lander", "Run The World", "https://runtheworld.example",
              [_cap(status=200, bytes=300, title="", visible=""),
               _cap(status=200, ua="render", bytes=30000,
                    final_url="https://runtheworld.example/lander",
                    title="",
                    visible="Related Searches run the world Copyright (c) 1999-2026 "
                            "GoDaddy, LLC. All rights reserved.")],
              "DEAD", ""))
    # An acquisition that forwards to the acquirer's own site and KEEPS the brand
    # is an ordinary redirect and stays LIVE (real: guildeducation.com ->
    # guild.com, ninjacart.in -> ninjacart.com).
    F.append(("acquirer-kept-brand-is-live", "Guild Education", "https://www.guildeducation.com",
              [_cap(status=200, bytes=90000,
                    final_url="https://guild.com/",
                    title="Education Benefits That Power Workforce Strategy",
                    visible="Guild helps employers attract and retain talent.")],
              "LIVE", ""))
    # ...but one that LOSES the brand is a policy call, so it queues for a human
    # rather than being admitted (owner decision 2026-09-19). Real: Hysolate.
    F.append(("acquirer-lost-brand-goes-to-admin", "Hysolate", "https://hysolate.com/",
              [_cap(status=200, bytes=90000,
                    final_url="https://www.fortinet.com/products/fortimail-workspace-security",
                    title="FortiMail Workspace Security | Fortinet",
                    visible="Fortinet Products Solutions Support Partners Company")],
              "MOVED", "policy:owner-changed"))
    # A short brand yields NO brand tokens at all (brand_tokens keeps length >= 4),
    # so "no token of the company appears on the page" would be vacuously true for
    # ANY redirect: the MOVED rule needs tokens to exist before it can claim they
    # are absent. A rebrand or platform move by a short-named company stays LIVE.
    # (Found by the 2026-09-19 critique, docs/liveness-funnel-plan.md F3.)
    F.append(("short-brand-redirect-stays-live", "Mux", "https://mux.com",
              [_cap(status=200, bytes=90000,
                    final_url="https://mux.dev/",
                    title="Mux - Video infrastructure for developers",
                    visible="Mux builds video APIs for developers. Pricing Docs "
                            "Customers Blog")],
              "LIVE", ""))
    # Legal seizure: nothing in the old vocabulary matched it, so a confiscated
    # domain read as LIVE.
    F.append(("seized-domain", "OldCo", "https://oldco.example",
              [_cap(status=200, bytes=900,
                    title="This domain has been seized",
                    visible="This domain has been seized by Homeland Security "
                            "Investigations in accordance with a court order.")],
              "DEAD", ""))
    # Banned category: the site is up and the business is real - we just do not
    # list this kind. Rejected automatically, never queued for a human.
    F.append(("banned-category", "LuckySpin", "https://luckyspin.example",
              [_cap(status=200, bytes=70000,
                    title="LuckySpin - Sports Betting and Poker Room",
                    visible="Sports betting, poker room and casino bonus. "
                            "Free spins for every new member.")],
              "BANNED", "policy:banned-category"))
    # ...and the false positive that keeps the two-tier rule honest: a payments
    # company that mentions "casino" once is not a casino.
    F.append(("mentions-casino-once", "PayFlow", "https://payflow.example",
              [_cap(status=200, bytes=80000,
                    title="PayFlow - Payments infrastructure for modern businesses",
                    visible="PayFlow powers payments for marketplaces including one "
                            "casino operator in Macau.")],
              "LIVE", ""))

    # ...and the false positives that shaped the rule. Every one of these was a
    # real BANNED verdict on the live archive before the marker list was narrowed
    # to commercial offers - a company may name the industries it serves.
    F.append(("names-industry-database", "Cockroach Labs", "https://www.cockroachlabs.com/",
              [_cap(status=200, bytes=120000,
                    title="CockroachDB - the most highly evolved SQL database",
                    visible="Trusted by gaming, streaming and gambling platforms "
                            "worldwide.")],
              "LIVE", ""))
    F.append(("names-industry-pharmacy", "PharmEasy", "https://pharmeasy.in/",
              [_cap(status=200, bytes=120000,
                    title="PharmEasy - India's largest online pharmacy",
                    visible="Order medicines online. Adult and paediatric care, health "
                            "talks, insurance and loans.")],
              "LIVE", ""))
    F.append(("mentions-payday-loans-once", "Brightside", "https://www.gobrightside.com/",
              [_cap(status=200, bytes=120000,
                    title="Brightside - Financial care for working families",
                    visible="We help members escape payday loans and build a safety "
                            "net.")],
              "LIVE", ""))

    F.append(("domain-may-be-for-sale", "HealthIQ", "https://www.healthiq.com",
              [_cap(status=200, bytes=3000,
                    title="HealthIQ.com domain name may be for sale",
                    visible="HealthIQ.com This domain name may be for sale Contact us "
                            "I'm not a robot Protected by ALTCHA")],
              "DEAD", ""))

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


def _gate_fixtures() -> list[tuple[str, str, dict[str, Any], str]]:
    """(label, url, cap kwargs, expected verdict). Every case is a real page from
    the pilot-50 run, so the gate is pinned against what the web actually served."""
    return [
        ("company-pricing", "https://atoms.dev",
         {"status": 200, "bytes": 60000,
          "title": "Atoms: Build websites & apps with AI, no code needed",
          "visible": "Resources Community About Pricing Log in Sign up Trusted by "
                     "builders from Turn ideas into products that sell"}, COMPANY),
        # A company whose site also has a docs section: commercial intent wins.
        ("company-with-docs", "https://daytona.io",
         {"status": 200, "bytes": 70000,
          "title": "Daytona - Secure Infrastructure for Running AI-Generated Code",
          "visible": "Docs Customers Pricing Startups Blog Sign in Contact us Run "
                     "AI Code. Secure and Elastic Infrastructure"}, COMPANY),
        ("docs-site", "https://reactnative.dev",
         {"status": 200, "bytes": 90000,
          "title": "React Native - Learn once, write anywhere",
          "visible": "Skip to main content React Native Docs Guides Components "
                     "APIs Architecture Releases Contributing Community Blog"},
         NOT_COMPANY),
        ("community-project", "https://syncthing.net",
         {"status": 200, "bytes": 50000, "title": "Syncthing",
          "visible": "Syncthing Project Downloads Security Foundation Docs Forum "
                     "Code Donations continuous file synchronization program"},
         NOT_COMPANY),
        # The host alone decides: a GitHub Pages path is not a company site.
        ("project-host-github-pages", "https://iptv-org.github.io",
         {"status": 200, "bytes": 3000, "title": "iptv-org",
          "visible": "iptv-org Search Found channel(s) Search syntax"}, NOT_COMPANY),
        ("project-host-telegram", "https://t.me/g4f_channel",
         {"status": 200, "bytes": 3000, "title": "", "visible": ""}, NOT_COMPANY),
        # Free hosting: a company may use it, or a side project may. REVIEW.
        ("free-host-review", "https://my-thing.netlify.app",
         {"status": 200, "bytes": 3000, "title": "My Thing",
          "visible": "A thing I made on a weekend"}, REVIEW_GATE),
        # A JS shell that shows only the brand name: no evidence either way, but
        # not a project page either, so it passes without a human.
        ("brand-only-shell", "https://fontawesome.com",
         {"status": 200, "bytes": 4000, "title": "Font Awesome",
          "visible": "Font Awesome"}, UNVERIFIED),
        # A real biotech with a brochure site and no commercial vocabulary.
        ("brochure-site-unverified", "https://fountaintx.com",
         {"status": 200, "bytes": 30000, "title": "Fountain Therapeutics",
          "visible": "Home Pipeline About Platform Our lead programs first-in-class "
                     "therapies"}, UNVERIFIED),
    ]


def run_selftest(args: argparse.Namespace, log: Log) -> int:
    fails = 0
    total = 0
    fixtures = _fixtures()
    for label, name, url, caps, want_state, want_class in fixtures:
        for c in caps:
            # a fixture only asserts a domain move when it says so explicitly
            c["url"] = c.get("url") or url
            c["final_url"] = c.get("final_url") or url
            c["_sig"] = signals(c, name, CFG)
        res = classify(name, url, caps, CFG)
        ok = res["state"] == want_state and (
            not want_class or res.get("evidence_class") == want_class)
        mark = "ok  " if ok else "FAIL"
        if not ok:
            fails += 1
        total += 1
        log(f"  [{mark}] {label:<32} {res['state']:<11} "
            f"{res.get('evidence_class') or '-':<16} {res['why'][:64]}")
    log("")
    log("  --- company gate (is this a company, or a project page?) ---")
    for label, url, kw, want in _gate_fixtures():
        cap = _cap(**kw)
        cap["url"] = cap.get("url") or url
        cap["final_url"] = cap.get("final_url") or url
        sig = signals(cap, kw.get("name", ""), CFG)
        res = company_gate(url, sig, CFG)
        ok = res["verdict"] == want
        if not ok:
            fails += 1
        total += 1
        log(f"  [{'ok  ' if ok else 'FAIL'}] {label:<32} {res['verdict']:<11} "
            f"{res['why'][:64]}")
    log(f"selftest: {total - fails}/{total} fixtures pass")
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
    p.add_argument("--per-host-delay", type=float, default=dflt(1.0),
                   help="min seconds between request starts to one host "
                        "(politeness; 0 disables the interval)")
    p.add_argument("--per-host-concurrency", type=int, default=dflt(2),
                   help="max in-flight requests to one host")
    p.add_argument("--ignore-robots", action="store_true", default=D,
                   help="do not read robots.txt (the politeness gate still spaces "
                        "requests; full rollback = --per-host-delay 0 too)")
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

    # render
    r = sub.add_parser("render", help="settle non-LIVE rows with a real browser "
                                      "(writes states-merged.json; drop prefers it)",
                       parents=[common])
    r.add_argument("--run", required=True, help="run directory")
    r.add_argument("--states", default="UNKNOWN,WALLED,MOVED",
                   help="which states to render (comma separated)")
    r.add_argument("--limit", type=int, help="only the first N selected rows")
    r.add_argument("--chrome",
                   help="path to Chrome/Chromium (default: CHROME_PATH or autodetect)")
    r.add_argument("--wait-ms", type=int, default=1500,
                   help="settle wait after networkidle (default 1500)")

    # drop
    d = sub.add_parser("drop", help="delete DEAD/REPURPOSED rows (dry-run by default)",
                       parents=[common])
    d.add_argument("--run", required=True, help="run directory with states.json")
    d.add_argument("--states-file",
                   help="state file to read (default <run>/states.json). Point this at a "
                        "merged state file when rows were settled by the browser pass.")
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

    # qa (Sequence 4): sampled QA of a run -> worksheet -> recorded verdicts.
    # The resulting qa-result.json is what the import endpoint reads to enforce
    # the auto-approval error budget (a breach refuses the import).
    q = sub.add_parser("qa", help="sampled QA: stratified worksheet for a run, "
                                  "--record ingests verdicts (feeds the import "
                                  "error budget)", parents=[common])
    q.add_argument("--run", required=False, default=None,
                   help="run directory with states.json (or states-merged.json); "
                        "omit when --sweep")
    q.add_argument("--record", action="store_true",
                   help="ingest the completed qa-worksheet.csv into qa-result.json "
                        "(computes the false-approval rate against the budget)")
    q.add_argument("--sweep", action="store_true",
                   help="ignore --run: sample machine-admitted archive rows from "
                        "the last --sweep-days into a fresh sweep run directory")
    q.add_argument("--sweep-days", type=int, default=7,
                   help="qa --sweep window (default 7)")
    q.add_argument("--db", help="qa --sweep: the archive sqlite file (read-only)")
    q.add_argument("--seed", type=int, default=7,
                   help="sample seed (same seed -> same worksheet; default 7)")
    q.add_argument("--rate", type=float, default=QA_SAMPLE_RATE,
                   help="LIVE sample rate (default 0.02 = 2 percent)")
    q.add_argument("--floor", type=int, default=QA_SAMPLE_FLOOR,
                   help=f"minimum LIVE rows in the sample (default {QA_SAMPLE_FLOOR})")
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
        if args.cmd == "render":
            return run_render(args, log)
        if args.cmd == "report":
            return run_report(args, log)
        if args.cmd == "drop":
            return run_drop(args, log)
        if args.cmd == "qa":
            return run_qa(args, log)
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
