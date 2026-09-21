"""liveness_rules - the canonical liveness/repurposing classifier, as pure functions.

WHY THIS FILE EXISTS
--------------------
The rules used to live inside `site_liveness_audit.py` only, which meant the app
could not consult them: the backend's weekly verify pass judged a site by its
HTTP status alone, and four gambling-spam domains sat in the archive as
`verified=1` on a bare "HTTP 200" until a human noticed (audit review,
2026-09-18). This module is the extraction of everything that is pure - the
vocabulary, the signal extraction and the classifier - so that the audit CLI and
the backend classify with ONE rule set. The CLI's `selftest` (50 fixtures, every
one a real incident) runs against THIS module, so any consumer is pinned by the
same fixtures.

The canonical copy lives in the app package (`backend/app/`) because the
deployable unit must carry its own rules; the audit CLI imports it from there
(see the shim at the top of `scripts/site_liveness_audit.py`).

Nothing here touches the network or a database. Capture (HTTP, caching, the
browser pass) stays in `site_liveness_audit.py`; deciding what a verdict means
(a strike vs a skip vs an admission) stays with each caller.

THE DOCTRINE (same as the CLI's; kept short here, full version there)
---------------------------------------------------------------------
1. A 200 is not proof of life.
2. A 403 is not proof of death.
3. One HTTP client is not evidence.
4. "Is it still this company?" is the right question, not "is it up?"
5. Short foreign words are never bare substrings.
6. A company may be named after a CDN.
7. Scan visible text, not raw HTML.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import re
import threading
import time
import unicodedata
from typing import Any, Iterable
from urllib.parse import urlparse


# ===========================================================================
# 1. Vocabulary. Everything a rule looks at lives here so another corpus can be
#    handled with --config instead of a code edit.
# ===========================================================================

import hashlib
import html as _html
import json
import re
import threading
import time
import unicodedata
from typing import Any, Iterable
from urllib.parse import urlparse


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
        # Found by the pilot-50 run: healthiq.com renders "This domain name may be
        # for sale" with a contact form and a captcha. The list had "domain is for
        # sale" but not the "may be" phrasing, so a for-sale lander was admitted as
        # LIVE. The domain word is required deliberately - a bare "may be for sale"
        # would match any marketplace sentence about goods.
        "domain name may be for sale", "this domain may be for sale",
        "domain may be for sale",
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
    # Registrar-lander boilerplate. Found by the browser pass: the parked page for
    # godutchpay.in says only "Related Searches ... Copyright (c) 1999-2026 GoDaddy,
    # LLC" - no "parked", no "for sale". "related searches" alone is far too
    # generic to flag, so it is deliberately absent; the copyright line and
    # "get this domain" are specific to a lander.
    "lander_phrases": [
        "courtesy of godaddy", "godaddy, llc", "get this domain",
        "this domain is parked", "this page is parked",
    ],
    # ...and the URL shapes only a parking service produces. A homepage served at
    # /lander is a registrar landing page; no real company site does that.
    "park_path_markers": [
        "/lander", "cgi-sys/defaultwebpage.cgi", "/domain-parking",
        "/parked-domain", "/cgi-sys/",
    ],
    # The parked-domain monetisation redirect: the query string echoes the domain
    # the visitor asked for, plus the parking network's own ids. Seen on
    # behalf.com, which now forwards to a news portal called HeadlineLogic.
    "monetisation_params_regex": (
        r"[?&](pcid=[0-9]+|d=[a-z0-9.-]+\.[a-z]{2,}|brand=[a-z0-9.-]+\.[a-z]{2,})"
    ),
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
        # found by the browser pass: SiteGround's captcha interstitial returns 202
        # with an empty HTTP body, so only a renderer ever sees it
        "robot challenge screen", "sgcaptcha",
        "checking the site connection security",
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
    # --- legal seizure / takedown: the domain is not the company's any more ----
    # Nothing in the old vocabulary matched a seizure banner, so a confiscated
    # domain read as LIVE. A seized domain is a machine-reject, not a queue item.
    "seizure_phrases": [
        "this domain has been seized", "domain has been seized",
        "this website has been seized", "seized by the", "seized pursuant to",
        "homeland security investigations", "immigration and customs enforcement",
        "national intellectual property rights coordination",
        "in accordance with a court order", "court-ordered seizure",
        "this site has been taken down", "website taken down by court order",
    ],
    # --- banned category: a live business we choose not to list ----------------
    # NOT a death (the site is up) and NOT repurposing (the company is real).
    # Checked AFTER class A/B/C on purpose: a hijacked domain serving a casino
    # should still be reported as REPURPOSED, because that is the more useful
    # fact (your domain was taken) than (a casino lives here).
    #
    # These markers are commercial-OFFER phrasing, not topic vocabulary, and one
    # only counts in the TITLE or as one of TWO distinct hits. The first draft of
    # this rule scanned topic words ("casino", "gambling", "adult", "loan",
    # "streaming", "pharmacy") and rejected SEVEN real companies on this very
    # archive: Cockroach Labs (a database) on "gambling"+"streaming", Conduktor
    # on "adult"+"streaming", PharmEasy and Pelago on "pharmacy"+"adult", Aura
    # on "adult"+"loan", Brightside on one mention of the payday loans it exists
    # to replace. A company site may name the industries it serves; only an offer
    # is an offer.
    "banned_markers": [
        "casino bonus", "free spins", "no deposit bonus", "deposit bonus",
        "welcome bonus", "poker room", "bookmaker", "betting odds",
        "sports betting", "sportsbook", "live dealer",
        "adult webcam", "escort service", "porn videos", "live sex",
        "torrent download", "cracked software", "warez",
        "payday loan", "payday loans", "cash advance loan",
        "no credit check loan", "instant payday",
    ],
    "banned_min_text_hits": 2,
    # --- company gate: is this candidate a company, or a project page? --------
    # The liveness funnel answers "is this link alive, and whose is it". It cannot
    # answer "is this a company" - and the pilot showed why that matters: a
    # GitHub-homepage channel yields reactnative.dev, d3js.org, pptr.dev, an
    # awesome-list and a Telegram channel, all of which the funnel correctly
    # called LIVE. This gate runs BEFORE admission and before enrichment, so a
    # docs page never costs 3 fetches and 2 LLM calls.
    #
    # Precision-first, exactly like every other rule here: reject only on
    # high-confidence evidence, accept on commercial intent, and send the rest to
    # REVIEW rather than guessing. REVIEW is not "publish".
    "project_hosts": [
        "github.io", "gitlab.io", "readthedocs.io", "t.me", "telegram.me",
        "discord.gg", "npmjs.com", "pypi.org", "crates.io", "packagist.org",
        "rubygems.org", "sourceforge.net", "hub.docker.com",
    ],
    # Free hosts: a real company may use one, and so does every side project.
    # REVIEW, never a silent drop.
    "review_hosts": [
        "netlify.app", "vercel.app", "pages.dev", "web.app", "firebaseapp.com",
        "herokuapp.com", "glitch.me", "replit.app", "notion.site", "medium.com",
        "wordpress.com", "blogspot.com",
    ],
    # Commercial intent. One hit is enough - these are things a documentation
    # site does not say.
    "commercial_signals": [
        "pricing", "book a demo", "request a demo", "get a demo",
        "request a meeting", "contact sales", "talk to sales", "start free trial",
        "free trial", "trusted by", "case studies", "our customers",
        "we're hiring", "careers", "buy now", "add to cart", "shop now",
        "request a quote", "get a quote", "get started free",
    ],
    # Project / docs / community vocabulary. Needs project_marker_min DISTINCT hits
    # AND no commercial signal before it means anything - a real company has a docs
    # section, so "docs" alone must never be enough.
    "project_markers": [
        "open source", "open-source", "contributing", "fork me on github",
        "pull request", "stargazers", "donations", "community-driven",
        "documentation", "api reference", "guides", "tutorial", "cheat sheet",
        "wiki", "changelog", "release notes", "downloads", "releases", "sponsor",
        "docs", "forum", "issues", "download",
    ],
    "project_marker_min": 3,
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

_CFG_HASH = ""


def load_config(path: str | None) -> dict[str, Any]:
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


def config_hash() -> str:
    """Hash of the active vocabulary, stamped into runs and manifests.

    Lazy on DEFAULT_CONFIG so a backend process that never called load_config
    still reports the same hash the CLI would for the built-in vocabulary.
    """
    global _CFG_HASH
    if not _CFG_HASH:
        _CFG_HASH = hashlib.sha256(
            json.dumps(DEFAULT_CONFIG, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return _CFG_HASH


# ===========================================================================
# 2. Small helpers (pure)
# ===========================================================================
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


def decode_body(body: bytes, charset: str | None) -> str:
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
# 3. Signal extraction + classification (pure functions; offline-testable)
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
    sig["lander"] = _phrase_hits(hay, cfg.get("lander_phrases") or [])
    final_url = str(cap.get("final_url") or cap.get("url") or "")
    try:
        fpath = urlparse(final_url).path.lower()
    except Exception:  # noqa: BLE001
        fpath = ""
    sig["park_path"] = [m for m in (cfg.get("park_path_markers") or []) if m in fpath]
    sig["monetised_redirect"] = bool(re.search(
        cfg.get("monetisation_params_regex") or "(?!)", final_url, re.I))
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

    # --- legal seizure, and banned-category content ---------------------------
    sz = _phrase_hits(hay, cfg.get("seizure_phrases") or [])
    sig["seizure_title"] = [p for p in sz if p in title.lower()]
    sig["seizure_body"] = [] if sig["seizure_title"] else (
        [p for p in sz if small or not title])
    sig["seizure"] = sig["seizure_title"] or sig["seizure_body"]

    bm = []
    for phrase in cfg.get("banned_markers") or []:
        rx = re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b", re.I)
        if rx.search(low):
            bm.append(phrase)
    bmin = int(cfg.get("banned_min_text_hits") or 2)
    btitle = [p for p in bm if p in title.lower()]
    sig["banned"] = btitle or (bm if len(bm) >= bmin else [])
    sig["banned_tier"] = ("title" if btitle else
                          ("marker-cluster" if len(bm) >= bmin else ""))

    # company-gate signals (see company_gate below)
    sig["commercial"] = _phrase_hits(hay, cfg.get("commercial_signals") or [])
    sig["project_markers"] = _phrase_hits(hay, cfg.get("project_markers") or [])

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


COMPANY = "company"
UNVERIFIED = "unverified"
NOT_COMPANY = "not_company"
REVIEW_GATE = "review"


def company_gate(url: str, sig: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Is this candidate a company/product, or a project / docs / community page?

    Runs BEFORE admission and BEFORE enrichment (docs/scale-to-10000-plan.md §3.5).
    The liveness pass cannot answer this: the pilot-50 run admitted reactnative.dev,
    d3js.org, ohmyz.sh, an awesome-list and a Telegram channel, all correctly LIVE.

    Order matters, and it is the opposite of intuition:
      1. a project-hosting host is a reject on its own (github.io, t.me, pypi.org);
      2. a free host is REVIEW, never a drop - real companies use them too;
      3. COMMERCIAL INTENT WINS: pricing/signup/demo/careers make it a company even
         if the page also has a docs section, which is why this is checked before
         the project markers;
      4. a cluster of project markers with no commercial signal is a reject;
      5. everything else is UNVERIFIED - admit-eligible, but carrying no positive
         evidence that a company lives there.

    UNVERIFIED is deliberately NOT a human queue. The first draft of this gate
    sent every row without commercial vocabulary to REVIEW, which on the pilot's
    50 candidates meant 23 review items - more than the 17 the liveness funnel was
    already escalating - because "we could not read the page" and "we read a
    personal project" are different things, and only the second is the gate's
    business. The gate REMOVES obvious non-companies; the liveness/admin path
    still decides everything else. A channel is judged by how many of its rows
    come back COMPANY rather than by how many queue for a human.

    Returns {"verdict": company|unverified|not_company|review, "why": str}.
    """
    host = host_of(url)
    for h in cfg.get("project_hosts") or []:
        if host == h or host.endswith("." + h):
            return {"verdict": NOT_COMPANY,
                    "why": f"host {host} is a project/community platform"}
    for h in cfg.get("review_hosts") or []:
        if host == h or host.endswith("." + h):
            return {"verdict": REVIEW_GATE,
                    "why": f"host {host} is free hosting - a company may use it, "
                           "or a side project may"}
    commercial = sig.get("commercial") or []
    markers = sig.get("project_markers") or []
    if commercial:
        return {"verdict": COMPANY,
                "why": f"commercial intent: {', '.join(commercial[:4])}"}
    if len(markers) >= int(cfg.get("project_marker_min") or 3):
        return {"verdict": NOT_COMPANY,
                "why": f"project/docs/community page ({', '.join(markers[:5])}) "
                       "with no commercial signal"}
    return {"verdict": UNVERIFIED,
            "why": "no project markers found, but no commercial evidence either "
                   f"(markers: {markers[:3] or 'none'})"}


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
        if sig["park"] or sig["park_path"] or sig["lander"] or sig["marketplace_host"]:
            detail = (", ".join(sig["park"][:3]) or ", ".join(sig["lander"][:2])
                      or ", ".join(sig["park_path"][:2]) or "marketplace host")
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
        # legal seizure / takedown: the domain is no longer the company's
        if sig["seizure"]:
            res.update(state="DEAD",
                       why=f"legal seizure / takedown notice "
                           f"({', '.join(sig['seizure'][:2])})")
            return res
        if sig["class_a"]:
            res.update(state="REPURPOSED", evidence_class="A:spam-keyword",
                       why="domain now sells unrelated gambling/piracy/SEO spam "
                           f"[{sig['spam_tier']}] ({'; '.join(sig['spam'][:5])})")
            return res
        # class C: the domain was parked and is now monetised. It forwards to a
        # parking network with the requested domain echoed in the query string and
        # says nothing about the company that used to be here. Found by the
        # browser pass on behalf.com, which now serves a "news portal".
        if (sig["monetised_redirect"] and not sig["title_has_brand"]
                and not sig["text_has_brand"]):
            res.update(state="REPURPOSED", evidence_class="C:monetised-redirect",
                       why="domain parked and monetised: forwards to "
                           f"{host_of(best.get('final_url'))} with the stored domain "
                           "echoed in the query string; no company token "
                           f"{sig['brand_tokens']} anywhere on the page")
            return res
        if sig["class_b"]:
            res.update(state="REPURPOSED", evidence_class="B:content-shell",
                       why="stock CMS shell: default artefact "
                           f"{','.join(sig['shell_strong'])}, generic title "
                           f"{best.get('title','')[:40]!r}, no company token "
                           f"{sig['brand_tokens']} in title or visible text")
            return res
        # banned category: live, real, and not ours to list. Checked after the
        # repurposing classes so a hijacked domain still reports as REPURPOSED.
        if sig["banned"]:
            res.update(state="BANNED", evidence_class="policy:banned-category",
                       why="live site in a category the archive does not list "
                           f"[{sig['banned_tier']}] ({'; '.join(sig['banned'][:5])})")
            return res
        # moved to a different owner: the stored domain now serves a live site
        # that mentions the company nowhere. An acquisition that kept the brand
        # (guildeducation.com -> guild.com) is NOT this; one that did not is a
        # policy call, so it goes to a human rather than being admitted.
        # The rule needs at least one brand token to look for: a name that yields
        # none (a short brand - "Mux", "Bun") would otherwise make "no token of
        # the company appears" vacuously true for ANY redirect. (2026-09-19.)
        if (res["redirected"] and sig["brand_tokens"]
                and not sig["title_has_brand"] and not sig["text_has_brand"]):
            res.update(state="MOVED", evidence_class="policy:owner-changed",
                       why=f"stored host {res['stored_host']} now serves "
                           f"{res['final_host']}, and no token of "
                           f"{sig['brand_tokens']} appears on the page")
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
# 4. The politeness gate (pure given an injected robots fetcher)
# ===========================================================================
class HostGate:
    """Per-registrable-domain admission for fetches.

    Why: the auditor runs a worker pool, and a corpus where one host appears
    many times (a GitHub channel, one registrar parking many domains) would be
    hammered concurrently - hostile-crawling territory and ban risk against
    the very sources the funnel depends on (the 2026-09-19 critique, F4).
    Enforced PER HOST (registrable domain):

      * a minimum interval between request starts;
      * a concurrency cap - at most N requests in flight to one host;
      * robots.txt (RFC 9309), fetched ONCE per host through the injected
        `robot_fetcher`; unreachable robots ALLOWS (nothing to read), a
        4xx robots ALLOWS (no policy published), a 5xx/429 robots DISALLOWS
        for the run (conservative: the server is already pushing back);
      * adaptive backoff: a 429/403 from the host GROWS that host's interval,
        a clean 2xx/3xx shrinks it back toward the configured delay.

    `reserve()` blocks on the CALLER's thread - a worker waits for its own
    host's slot - so the dispatcher should spread hosts across the work queue;
    workers then always find some host with capacity, and one host's delay
    never blocks another host's thread. `next_slot()` is the non-blocking form
    for a sequential caller (the renderer schedule).
    """

    def __init__(self, delay: float = 1.0, concurrency: int = 2,
                 respect_robots: bool = True, robot_fetcher=None):
        self.delay = max(0.0, float(delay))
        self.concurrency = max(1, int(concurrency))
        self.respect_robots = bool(respect_robots)
        self._robot_fetcher = robot_fetcher
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._last: dict[str, float] = {}       # host -> last acquire (monotonic)
        self._inflight: dict[str, int] = {}     # host -> in-flight count
        self._backoff: dict[str, float] = {}    # host -> extra delay seconds
        self._robots: dict[str, Any] = {}       # host -> parser | None (allowed)
        self._hlocks: dict[str, threading.Lock] = {}  # per-host robots locks
        self._rlock = threading.Lock()

    def reserve(self, host: str) -> float:
        """Block until `host` has capacity and its interval has passed.

        Returns the wait this caller actually spent (0 when the slot was
        immediately available) - useful for tests and logs.
        """
        with self._cond:
            while True:
                now = time.monotonic()
                last = self._last.get(host)
                earliest = (last + self.delay + self._backoff.get(host, 0.0)
                            if last is not None else now)
                if (self._inflight.get(host, 0) < self.concurrency
                        and now >= earliest):
                    self._inflight[host] = self._inflight.get(host, 0) + 1
                    self._last[host] = now
                    return max(0.0, now - earliest)
                self._cond.wait(timeout=0.05)

    def release(self, host: str) -> None:
        with self._cond:
            self._inflight[host] = max(0, self._inflight.get(host, 0) - 1)
            self._cond.notify_all()

    def next_slot(self, host: str) -> float:
        """Non-blocking form for a sequential caller: advance this host's clock
        and return the earliest monotonic time it may be hit again (0 = now)."""
        with self._cond:
            now = time.monotonic()
            last = self._last.get(host)
            earliest = (last + self.delay + self._backoff.get(host, 0.0)
                        if last is not None else now)
            self._last[host] = max(now, earliest)
            return self._last[host]

    def record_result(self, host: str, status: Any) -> None:
        """Adaptive per-host backoff: pushback grows the interval, success
        shrinks it. Deliberately bounded so one hostile host cannot wedge."""
        with self._cond:
            cur = self._backoff.get(host, 0.0)
            try:
                st = int(status)
            except (TypeError, ValueError):
                return
            if st in (403, 429):
                self._backoff[host] = min(cur + max(0.5, self.delay), 30.0)
            elif 200 <= st < 400 and cur > 0:
                self._backoff[host] = max(0.0, cur - max(0.5, self.delay) / 2)

    def penalty(self, host: str) -> float:
        """Current adaptive backoff for a host (seconds) - for logs and tests."""
        with self._lock:
            return self._backoff.get(host, 0.0)

    # --- robots.txt ---------------------------------------------------------
    def robots_allowed(self, url: str, host: str) -> bool:
        if not self.respect_robots:
            return True
        rp = self._robots_for(host)
        if rp is None:
            return True
        try:
            return bool(rp.can_fetch("*", url))
        except Exception:  # noqa: BLE001 - an unreadable policy never blocks
            return True

    def _robots_for(self, host: str):
        # Per-host lock: host A's robots read (a slow network call) must never
        # serialize host B's. A single global lock here made 1,258 robots
        # fetches one serial queue and throttled the whole audit to ~1.4 rows/s
        # (found live, 2026-09-19) - hence the lock-per-host + re-check dance.
        with self._rlock:
            if host in self._robots:
                return self._robots[host]
            hlock = self._hlocks.setdefault(host, threading.Lock())
        with hlock:
            with self._rlock:
                if host in self._robots:
                    return self._robots[host]
            rp = None
            if self._robot_fetcher is not None:
                try:
                    rp = self._robot_fetcher(host)
                except Exception:  # noqa: BLE001 - unreadable robots allows
                    rp = None
            with self._rlock:
                self._robots[host] = rp
            return rp

