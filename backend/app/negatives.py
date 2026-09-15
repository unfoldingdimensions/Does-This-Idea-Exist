"""Negative claims — the strictest rule in the product (F-09, spec §8.2).

A negative is **an observation about a page that enumerates**, never a verdict
about the world:

    ✅ "Pricing page lists Free / Pro / Team — no self-host tier."
       — a fact about a page the reader can open.
    ❌ "Acme has no self-host tier."
       — our assertion, resting on nothing anyone said.
    ❌ "No API" derived from a 404 on a guessed acme.com/api URL.
       — a 404 on a guessed URL is not evidence of absence.

Only pages that enumerate the whole set count (a pricing page listing every
tier, a docs index listing every section, a footer listing every store link).
A page that renders client-side and returns an empty shell is "we could not read
it" — `unknown` at low confidence, never "they don't have it". And if no
enumerating page can be read, the cell is `unknown`, which is itself useful
signal ("go check whether they have an API").

The rule is enforced here in three places, not by convention:

  1. `probe_absence` refuses any page whose ROLE is not an enumerating role. The
     guessed capability paths (/api, /self-host, /mobile) are never in the page
     plan and have no record, so they cannot produce a row — there is no code
     path that fetches them.
  2. An unreadable enumerating page yields `unknown`, not a negative.
  3. `validate` — the LLM pass's only entry point — refuses any negative whose
     `observed_on` is not a URL we actually READ and that ENUMERATES.

Order is deterministic first, LLM second: the probes are facts about pages, and
a model does not get to overrule them.
"""
import re

from . import pages as pages_mod
from . import teardown as td

# Roles that enumerate a whole set: the only pages a negative may come from.
ENUMERATING_ROLES = (pages_mod.ROLE_PRICING, pages_mod.ROLE_DOCS)
# Roles whose links enumerate reachable surfaces (the footer/store-link probe).
LINK_ROLES = (pages_mod.ROLE_HOME, pages_mod.ROLE_PRICING, pages_mod.ROLE_DOCS)
# Capabilities we never guess a URL for. Documented so the intent survives.
GUESSED_CAPABILITY_PATHS = ("/api", "/self-host", "/mobile", "/android", "/ios")

CAP_FREE_TIER = "free tier"
CAP_SELF_HOST = "self-host"
CAP_API = "API"
CAP_MOBILE = "mobile app"

SELF_HOST_HINTS = (
    "self-host", "self host", "selfhost", "self-hosted", "on-prem", "on prem",
    "on premise", "on-premise", "private cloud", "your own server",
)
API_HINTS = ("api", "rest", "graphql", "sdk", "webhook", "endpoint")
STORE_HINTS = ("apps.apple.com", "itunes.apple.com", "play.google.com", "app store", "google play")


def _text(value) -> str:
    return td._text(value)


def _obs(page: dict, claim: str, why: str, confidence: float) -> dict:
    """An observation about a page we read. `observed_on` is a URL the reader can
    click, and `why` names what the page actually listed."""
    return {
        "claim": claim,
        "observed_on": page.get("url") or "",
        "why": why,
        "confidence": confidence,
        "value": f"observed: {why}",
    }


def unknown_observation(page: dict, capability: str) -> dict:
    """`unknown` for a page that enumerates but that we could not read.

    Low confidence on purpose: it records that the question was asked and not
    answered, which is different from both a negative and silence.
    """
    return {
        "claim": f"{capability}: unknown",
        "observed_on": page.get("url") or "",
        "why": f"could not read the page ({page.get('reason') or page.get('state')}) — unknown, not absence",
        "confidence": td.CONF_UNKNOWN,
        "value": "unknown",
    }


def _listed(text: str, hints: tuple[str, ...]) -> bool:
    """Does this text list the thing? Word-boundary matching for the short hints,
    so 'capital' does not count as 'API'."""
    lowered = (text or "").lower()
    for hint in hints:
        pattern = r"\b" + re.escape(hint) + r"\b" if hint.isalpha() else re.escape(hint)
        if re.search(pattern, lowered):
            return True
    return False


def probe_absence(page: dict | None, capability: str, *, why: str, hints: tuple[str, ...],
                  roles: tuple[str, ...] = ENUMERATING_ROLES) -> dict | None:
    """One observation about one page — or None when the page cannot support one.

    None when there is no such page, when the page's role does not enumerate (a
    guessed URL), or when the page IS readable and lists the capability.
    Unknown (low confidence) when the page enumerates but could not be read.
    """
    if not page or not page.get("url"):
        return None
    if page.get("role") not in roles:
        return None
    if page.get("state") != pages_mod.STATE_READABLE:
        return unknown_observation(page, capability)
    if _listed(page.get("text") or "", hints):
        return None
    return _obs(page, f"no {capability}", why, td.CONF_NEGATIVE_DETERMINISTIC)


def mobile_absence(pages: dict, record=None) -> dict | None:
    """The footer / store-link probe: a mobile presence either exists or is not
    linked from a page that lists the links. Store columns count as evidence that
    it exists (F-19)."""
    home = (pages or {}).get(pages_mod.ROLE_HOME) or {}
    if not home.get("url") or home.get("role") not in LINK_ROLES:
        return None
    known = [str((record or {})[k] or "") if _has(record, k) else "" for k in ("app_store_url", "play_store_url")]
    if any(_listed(url, STORE_HINTS) for url in known):
        return None
    if home.get("state") != pages_mod.STATE_READABLE:
        return unknown_observation(home, CAP_MOBILE)
    if any(_listed(link, STORE_HINTS) for link in home.get("links") or []):
        return None
    return _obs(
        home,
        f"no {CAP_MOBILE}",
        "the page's own links list no App Store / Google Play link",
        td.CONF_NEGATIVE_DETERMINISTIC,
    )


def _has(row, key: str) -> bool:
    try:
        row[key]
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _tier_names(teardown: dict, pricing_page: dict) -> str:
    plans = ((teardown or {}).get("pricing") or {}).get("plans") or []
    names = [p.get("name") for p in plans if isinstance(p, dict) and p.get("name")]
    if names:
        return " / ".join(names[:6])
    return "the tiers on the page"


def deterministic(pages: dict, teardown: dict, record=None) -> list[dict]:
    """The probes, run first (F-09). No model involved: these are facts about the
    pages that enumerate, taken at face value because the link is right there."""
    out: list[dict] = []
    pricing_page = (pages or {}).get(pages_mod.ROLE_PRICING) or {}
    docs_page = (pages or {}).get(pages_mod.ROLE_DOCS) or {}
    pricing = (teardown or {}).get("pricing") or {}
    free_tier = _text(pricing.get("free_tier")).lower()

    # /pricing lists every tier -> it can say whether a free tier exists.
    if pricing_page.get("state") == pages_mod.STATE_READABLE:
        if free_tier and ("no free" in free_tier or free_tier.startswith("none") or free_tier in ("paid only", "no")):
            out.append(_obs(
                pricing_page, f"no {CAP_FREE_TIER}",
                f"pricing page states: {pricing.get('free_tier')}",
                td.CONF_NEGATIVE_DETERMINISTIC,
            ))
        neg = probe_absence(
            pricing_page, CAP_SELF_HOST,
            why=f"pricing page lists {_tier_names(teardown, pricing_page)} — no self-host tier",
            hints=SELF_HOST_HINTS,
        )
        if neg:
            out.append(neg)
    elif pricing_page.get("url"):
        # Could not read it: unknown, NOT "they don't have it".
        out.append(unknown_observation(pricing_page, CAP_FREE_TIER))
        out.append(unknown_observation(pricing_page, CAP_SELF_HOST))

    # /docs lists every section -> an API section either is listed or is not.
    if docs_page.get("state") == pages_mod.STATE_READABLE:
        neg = probe_absence(
            docs_page, CAP_API,
            why="the docs index lists no API section",
            hints=API_HINTS,
        )
        if neg:
            out.append(neg)
    elif docs_page.get("url"):
        out.append(unknown_observation(docs_page, CAP_API))

    mobile = mobile_absence(pages, record)
    if mobile:
        out.append(mobile)

    return [obs for obs in out if obs and obs.get("observed_on")]


_VERDICT_PREFIXES = (
    "they have no ", "they do not have ", "they don't have ", "has no ", "have no ",
    "does not have ", "doesn't have ", "do not have ", "lacks ",
)


def _as_observation(claim: str) -> str:
    """Turn a verdict-shaped claim into an observation, or keep what is there.

    "Acme has no self-host tier" is exactly the sentence the spec forbids us to
    print; the same fact, phrased as the page observation it is, is fine. We
    cannot re-derive the page's wording here, so the least dishonest fix is to
    drop the subject and keep the capability.
    """
    lowered = claim.lower()
    for prefix in _VERDICT_PREFIXES:
        idx = lowered.find(prefix)
        if idx != -1:
            rest = claim[idx + len(prefix):].strip()
            if rest:
                return f"no {rest}"
    return claim


def validate(raw: dict, pages: dict) -> dict | None:
    """The LLM pass's only entry point. Refuses anything that does not trace to a
    page we READ and that ENUMERATES — refused, not stored as a weak negative."""
    if not isinstance(raw, dict):
        return None
    claim = _text(raw.get("claim"))
    url = _text(raw.get("observed_on"))
    why = _text(raw.get("why"))
    if not claim or not url:
        return None
    allowed = {rec.get("url") for rec in pages_mod.enumerating(pages).values()}
    if url not in allowed:
        return None
    claim = _as_observation(claim)[:120]
    return {
        "claim": claim,
        "observed_on": url,
        "why": why[:240],
        "confidence": td.CONF_NEGATIVE_LLM,
        "value": (f"observed: {why}" if why else "observed")[:240],
    }


def _claim_key(claim: str) -> str:
    """A capability-level key for de-duplicating one competitor's negatives.

    "no self-host", "no self-host tier" and "no self-host support" are one
    observation, not three — the same capability-level grouping the gap table
    does (docs/gap-table-format.md §2), applied where a model and a probe can
    otherwise both report the same fact twice.
    """
    key = re.sub(r"[^a-z0-9 ]+", "", (claim or "").lower())
    key = re.sub(r"\b(tier|tiers|support|plan|plans|section|sections|mode|feature|features)\b", " ", key)
    return " ".join(key.split())


def capture(pages: dict, teardown: dict, record=None, llm_negatives=None) -> list[dict]:
    """Deterministic first, LLM second — over the already-fetched text only.

    The LLM may not fetch anything: it can only cite URLs that are already in
    `pages`, and anything else is dropped by `validate`. De-duplication is by
    capability, so the deterministic probe wins over the model's paraphrase of
    the same fact.
    """
    out = deterministic(pages, teardown, record)
    for raw in llm_negatives or []:
        neg = validate(raw, pages)
        if neg:
            out.append(neg)
    seen: set[str] = set()
    final: list[dict] = []
    for neg in out:
        key = _claim_key(neg.get("claim"))
        if not key or key in seen:
            continue
        seen.add(key)
        final.append(neg)
    return final
