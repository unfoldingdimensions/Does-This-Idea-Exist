"""Content-aware liveness rules for the app's verify pass and the funnel import.

One canonical rule set: this module re-exports `app.liveness_rules` — the same
rules the audit CLI (`site_liveness_audit.py`) runs its fixture selftest
against — so the weekly verify pass, the funnel import and the CLI classify
with identical vocabulary and identical rules.

WHERE THE RULES LIVE: `backend/app/liveness_rules.py`. The backend must be able
to import its own rules offline from its own package (the container image ships
`app/` and nothing else), so the canonical copy lives IN the app and the CLI is
the guest: `site_liveness_audit.py` finds this file by path when run from a
repo checkout (`scripts/` sits beside `backend/`). If the two ever become
separately deployed units, the CLI should vendor or pin the module explicitly
rather than reaching across.

Nothing here touches the network or the database. Callers fetch (netguard) and
decide what a verdict means:

  * verify.check_url_ok maps a verdict onto the tri-state contract —
    DEAD/REPURPOSED are genuine strikes, WALLED/UNKNOWN/MOVED/BANNED are skips,
    LIVE is unchanged;
  * funnel.import_run maps a saved run's states onto admissions and admin-queue
    entries, and never deletes.

This is the check that would have caught the four gambling/repurposed domains
the 2026-09-18 review found sitting in the archive as verified=1 on a bare
"HTTP 200" — the app's verifier only recorded the status code.
"""
from __future__ import annotations

from . import liveness_rules as rules  # the canonical module, inside the app

# States that mean the stored domain is genuinely no longer this company's —
# a verify strike (3 consecutive → the existing dead-flip), never instant death.
STRIKE_STATES = frozenset({"DEAD", "REPURPOSED"})
# States that mean "could not confirm, or a policy call" — never a strike.
# WALLED-style ambiguity must not accumulate strikes (three bot-walled runs
# must never dead-flip a healthy company — the WHOOP/Capterra incident).
SKIP_STATES = frozenset({"WALLED", "UNKNOWN", "MOVED", "BANNED", "NO_URL"})


def classify_homepage(
    name: str,
    url: str,
    *,
    status: int,
    text: str,
    final_url: str = "",
    nbytes: int = 0,
) -> dict:
    """Run the funnel's content rules over an already-fetched 2xx body.

    `text` is the decoded HTML; `nbytes` the body size in bytes (drives the
    short-page gates). Returns the classifier's result dict: state, why,
    evidence_class. Pure — no network, no DB.
    """
    cap: dict = {
        "url": url,
        "ua": "verify",
        "status": status,
        "error": "",
        "error_class": "",
        "final_url": final_url or url,
        "chain": [],
        "content_type": "text/html",
        "server": "",
        "bytes": nbytes if nbytes else len(text.encode("utf-8", "ignore")),
        "truncated": False,
        "blocked_by_guard": "",
        "html": text or "",
    }
    cfg = rules.DEFAULT_CONFIG
    low = (text or "").lower()
    # Shell artefacts pre-extracted the same way the CLI's capture does, so a
    # class-B (stock CMS shell) verdict is reachable here too.
    cap["shell_raw"] = [x for x in cfg["shell_markers_any"] if x in low]
    cap["shell_strong_raw"] = [x for x in cfg["shell_markers_strong"] if x in low]
    cap["title"] = rules.first_match(rules.TITLE_RE, text, 240)
    cap["meta_description"] = rules.first_match(rules.META_DESC_RE, text, 300)
    cap["h1"] = rules.first_match(rules.H1_RE, text, 200)
    cap["visible"] = rules.visible_text(text)
    cap["meta_refresh"] = rules.first_match(rules.META_REFRESH_RE, text, 300)
    cap["js_location"] = ""
    sig = rules.signals(cap, name or "", cfg)
    cap["_sig"] = sig
    return rules.classify(name or "", url, [cap], cfg)


def config_hash() -> str:
    """Hash of the active vocabulary — for run/receipt provenance parity."""
    return rules.config_hash()
