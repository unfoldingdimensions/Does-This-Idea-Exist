"""Bounding and writing the teardown fields (F-06, F-07, F-08) before the DB.

`enrich._clean_profile` clamps the identity profile; this is the same discipline
one level down. The page text is attacker-influenced (anyone can point a capture
at their own site) and the model is free to ignore its prompt, so everything is
bounded HERE — nothing raw reaches SQLite.

The rules that are not negotiable:

  * **features** — 5-10 short strings. Fewer than 5 from a real source means the
    field is UNKNOWN: we store `[]` and never pad it with invented capabilities.
  * **pricing** — rows are `{name, price, period}`. A malformed row is DROPPED
    rather than stored half-formed; every pricing write stamps
    `pricing_captured_at` and `pricing_source_url`, because pricing decays and an
    undated price is not evidence.
  * **positioning** — one line, capped.
  * JSON columns go through `json.dumps`. `_text()` is string-only: a dict passed
    through it becomes `"{'name': 'Pro'}"` in a JSON column, which parses as
    garbage and looks fine.

The writer also does the F-14 carve-out: a capture that learned nothing must not
erase a teardown that is already on file. An empty result is not an improvement.
"""
import json
import sqlite3

from . import enrich, evidence as ev, pages as pages_mod

FEATURES_MIN, FEATURES_MAX = 5, 10
FEATURE_MAX_CHARS = 80
POSITIONING_MAX_CHARS = 300
FREE_TIER_MAX_CHARS = 120

PERIODS = ("monthly", "annual", "one-time")
# Order matters: "annual" before "monthly" would not matter here, but "one-time"
# before "annual" does — "one-time annual" must not resolve to annual.
_PERIOD_HINTS = (
    ("one-time", "one-time"),
    ("one time", "one-time"),
    ("lifetime", "one-time"),
    ("forever", "one-time"),
    ("once", "one-time"),
    ("annual", "annual"),
    ("annually", "annual"),
    ("year", "annual"),
    ("yr", "annual"),
    ("month", "monthly"),
    ("mo", "monthly"),
)

# The provenance marker every machine-drafted teardown row carries until a human
# confirms (F-05). Kept beside the writer so no caller can invent its own label.
MACHINE_DRAFTED = enrich.MACHINE_DRAFTED

# Confidence is the retrieval-vs-assertion distinction (F-02): a claim read off a
# page is evidence; a page we could not read is unknown at low confidence.
CONF_FEATURE = 0.6
CONF_PRICING = 0.7
CONF_POSITIONING = 0.6
CONF_NEGATIVE_DETERMINISTIC = 0.8
CONF_NEGATIVE_LLM = 0.5
CONF_UNKNOWN = 0.1


def _text(value) -> str:
    return enrich._text(value)


def clean_features(raw) -> list[str]:
    """Bound a feature list to 5-10 short, unique strings — or [] (unknown).

    Below 5 the field is unknown, not "nearly there": padding it would invent
    capabilities, which is the one thing the teardown must never do.
    """
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = _text(item)
        if not text:
            continue
        # A 300-character "feature" is a paragraph, not a capability.
        if len(text) > FEATURE_MAX_CHARS:
            text = text[:FEATURE_MAX_CHARS].rstrip()
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    if len(out) < FEATURES_MIN:
        return []
    return out[:FEATURES_MAX]


def clean_positioning(raw) -> str:
    """One line, capped. The first line only — a positioning paragraph is a
    description, and `description` already exists."""
    text = _text(raw)
    if not text:
        return ""
    line = text.splitlines()[0].strip()
    return line[:POSITIONING_MAX_CHARS].strip()


def normalize_period(raw) -> str:
    """Map the model's billing-period words onto the three canonical values.

    Returns "" for anything unrecognisable — the caller drops the row rather
    than guessing a period (a wrong period is a wrong price).
    """
    text = _text(raw).lower()
    if text in PERIODS:
        return text
    for hint, period in _PERIOD_HINTS:
        if hint in text:
            return period
    return ""


def clean_plans(raw) -> list[dict]:
    """Plan rows `{name, price, period}`. A malformed row is dropped, not
    stored half-formed: a plan the reader cannot price is worse than no plan."""
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))[:80]
        price = _text(item.get("price"))[:80]
        period = normalize_period(item.get("period"))
        if not name or not price or not period:
            continue
        out.append({"name": name, "price": price, "period": period})
    return out


def clean_pricing(raw) -> dict:
    """`{free_tier, plans}` — the shape docs/teardown-spec.md §5.1 specifies."""
    if not isinstance(raw, dict):
        return {"free_tier": "", "plans": []}
    return {
        "free_tier": _text(raw.get("free_tier"))[:FREE_TIER_MAX_CHARS],
        "plans": clean_plans(raw.get("plans")),
    }


def clean_teardown(raw) -> dict:
    """The bounded teardown payload. Partial output is valid — every field that
    the source did not support comes back empty and is treated as unknown."""
    raw = raw if isinstance(raw, dict) else {}
    return {
        "features": clean_features(raw.get("features")),
        "positioning": clean_positioning(raw.get("positioning")),
        "pricing": clean_pricing(raw.get("pricing")),
        "negatives": [],
    }


def write_teardown(
    conn: sqlite3.Connection,
    startup_id: int,
    teardown: dict,
    pages: dict,
    *,
    captured_at: str | None = None,
    existing=None,
) -> dict:
    """Write the teardown columns and one evidence row per claim.

    Every feature, every plan, the free-tier line, the positioning line and every
    negative gets its own row with the page it came from — that is what makes the
    record a quotation with a citation rather than an opinion. Returns a summary
    the job and the verifier both read.
    """
    captured_at = captured_at or pages_mod.now()
    home = (pages or {}).get(pages_mod.ROLE_HOME) or {}
    pricing_page = (pages or {}).get(pages_mod.ROLE_PRICING) or {}
    home_url = home.get("url") or ""
    pricing_url = pricing_page.get("url") or ""

    existing_features = ""
    if existing is not None:
        try:
            existing_features = existing["features_json"] or ""
        except (KeyError, IndexError):
            existing_features = ""

    values: dict = {}
    summary: dict = {
        "features": 0,
        "plans": 0,
        "positioning": False,
        "negatives": 0,
        "unknown": [],
        "evidence_rows": 0,
        "captured_at": captured_at,
    }
    rows: list[dict] = []

    # --- features (F-06) -------------------------------------------------
    features = teardown.get("features") or []
    if features and home_url:
        values["features_json"] = json.dumps(features, ensure_ascii=False)
        summary["features"] = len(features)
        rows += [
            {
                "evidence_type": "feature",
                "source_url": home_url,
                "claim": feature,
                "value": feature,
                "provenance": MACHINE_DRAFTED,
                "confidence": CONF_FEATURE,
            }
            for feature in features
        ]
    else:
        # Unknown, honestly stored — unless a real list is already on file, which
        # a capture that learned nothing must not erase (F-14).
        if not existing_features:
            values["features_json"] = json.dumps([], ensure_ascii=False)
        summary["unknown"].append("features")

    # --- pricing (F-07) --------------------------------------------------
    pricing = teardown.get("pricing") or {"free_tier": "", "plans": []}
    plans = pricing.get("plans") or []
    free_tier = pricing.get("free_tier") or ""
    if pricing_page.get("state") == pages_mod.STATE_READABLE and pricing_url and (plans or free_tier):
        values["pricing_json"] = json.dumps(pricing, ensure_ascii=False)
        # Pricing decays: every pricing write carries when and where it was read.
        values["pricing_captured_at"] = captured_at
        values["pricing_source_url"] = pricing_url
        summary["plans"] = len(plans)
        for plan in plans:
            rows.append(
                {
                    "evidence_type": "pricing",
                    "source_url": pricing_url,
                    "claim": plan["name"],
                    "value": f"{plan['price']} / {plan['period']}",
                    "provenance": MACHINE_DRAFTED,
                    "confidence": CONF_PRICING,
                }
            )
        if free_tier:
            rows.append(
                {
                    "evidence_type": "pricing",
                    "source_url": pricing_url,
                    "claim": "free_tier",
                    "value": free_tier,
                    "provenance": MACHINE_DRAFTED,
                    "confidence": CONF_PRICING,
                }
            )
    else:
        # No readable pricing page -> no price, no capture stamp. A pricing write
        # without its date is exactly the undated price F-07 refuses to store.
        summary["unknown"].append("pricing")

    # --- positioning (F-08) ----------------------------------------------
    positioning = teardown.get("positioning") or ""
    if positioning and home_url:
        values["positioning"] = positioning
        summary["positioning"] = True
        rows.append(
            {
                "evidence_type": "positioning",
                "source_url": home_url,
                "claim": positioning,
                "value": positioning,
                "provenance": MACHINE_DRAFTED,
                "confidence": CONF_POSITIONING,
            }
        )
    else:
        summary["unknown"].append("positioning")

    # --- negatives (F-09) -------------------------------------------------
    for neg in teardown.get("negatives") or []:
        rows.append(
            {
                "evidence_type": "negative",
                "source_url": neg.get("observed_on") or "",
                "claim": neg.get("claim"),
                "value": neg.get("value") or neg.get("why") or "unknown",
                "provenance": MACHINE_DRAFTED,
                "confidence": neg.get("confidence"),
            }
        )
        summary["negatives"] += 1

    if values:
        if existing is None:
            # The teardown fields are written onto a record that already exists:
            # a capture is never the thing that creates the archive row, and
            # inventing a name here would file a nameless twin.
            raise ValueError(
                "write_teardown needs the existing row — a teardown is an UPDATE, "
                "not a new record"
            )
        values["source"] = values.get("source") or "website"
        # The normal seed writer: it applies stamp_provenance (F-05) and never
        # downgrades a human_confirmed row.
        enrich._upsert(conn, values, existing)

    if rows:
        summary["evidence_rows"] = ev.write_many(conn, startup_id, rows)

    return summary


def teardown_fields_present(row) -> bool:
    """Does this record already carry a teardown? Used by the JIT freshness check
    and by the F-14 carve-out tests."""
    if row is None:
        return False
    try:
        features = json.loads(row["features_json"] or "[]")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        features = []
    try:
        positioning = row["positioning"] or ""
    except (KeyError, IndexError):
        positioning = ""
    return bool(features) or bool(positioning)
