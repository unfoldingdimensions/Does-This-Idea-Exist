"""Comparison, the gap table and the three exports — Phase 3.

F-15 (`POST /api/compare`), F-16 (`GET /api/export/{markdown|json|csv}`),
F-17 (`GET /api/startups/{slug}`) and F-21 (the two trust badges, explicit).
The format is `docs/gap-table-format.md`; the field names it consumes are
`docs/teardown-spec.md` §5.1's canonical ones.

Four rules shape everything here, and they are the product rather than
decoration (`docs/gap-table-format.md` §3):

  * **Every "they" cell carries a source.**  A competitor claim is taken at face
    value *because* the link is right there — the product attributes, it does
    not adjudicate.  Pricing cells carry their `captured_at` as well, because
    pricing decays.
  * **A negative is an observation about a page that enumerates**, never a
    verdict about the world, and a claim that does not trace reads `unknown`,
    never "no".  Negatives only ever come from the capture's `negatives` module
    (which refuses a guessed URL and a page it could not read); a negative row
    here that somehow carries no source renders `unknown`.
  * **Every "you" cell comes from what the founder entered.**  This module never
    invents the founder's features — the `you` side is `founder.profile_of`, full
    stop.
  * **No verdict line.**  The table ends at the facts; the product may invite the
    founder to read the gaps, never prints "you should build X".

Two stores, one comparison.  The `you` record lives in the founder store
(`FOUNDER_DB_PATH`) and the competitors in the archive — so the request names the
sides (`{you: {...}, competitors: [...]}`) instead of passing one flat id list,
where `id=7` would be ambiguous across two files.  The cross-store diff is done
here, in Python: the band logic and the capability-level matching are not
expressible as SQL, and the two sides live in different files.

**Statelessness (F-16).**  There are no accounts and no server-side sessions, so
nothing here holds "the last comparison" in memory.  `/api/export` takes the same
inputs as `/api/compare` and recomputes deterministically — which is also why one
founder's comparison can never be read back by another request.  Exports are pure
reads: they never trigger a capture, so re-running one with the same inputs
yields the same bytes.

**Privacy posture (Phase 3, written down as the prompt requires).**  This is a
local-first, single-user product.  The founder store is a separate file and the
archive endpoints (`/api/startups`, `/api/stats`, `/api/categories`) never read
it; an export only ever exposes the founder record the caller named, and the
"you" side of a comparison is read on the same machine by id.  That is
acceptable *locally* — there are no accounts, so "the founder's own draft is
readable by id on the same machine" is the whole threat model.  The hosted
caveat is named in `docs/teardown-spec.md` §3.1: if an instance is hosted, the
founder's app sits in that instance's founder DB, so hosting must exclude
`FOUNDER_DB_PATH` from backups and the privacy copy must say which of the two is
true.  No endpoint here broadens that exposure.

Slug rule (documented in one place, F-17): a slug is the name lowercased, with
every run of non-alphanumeric characters replaced by a single hyphen and the
resulting ends trimmed — "Stability AI" -> "stability-ai", "Cal.com" ->
"cal-com", "Bun" -> "bun".  Collisions are expected, not hypothetical (the
archive already holds same-name groups for Stability AI, Motion, Fathom,
Cal.com, Bun and Bird, deliberately not auto-merged), so resolution is
deterministic: the human-verified row first, then the lowest id.  The resolved
id and name travel in the payload so a client can tell which row it received.
"""
import csv
import io
import json
import re

from . import capture, evidence as ev, founder

MAX_COMPETITORS = 3

# --- bands (docs/gap-table-format.md §1) -----------------------------------
BAND_YOU_HAVE = "you_have_they_dont"
BAND_THEY_HAVE = "they_have_you_dont"
BAND_BOTH = "both_have"
BAND_UNKNOWN = "unknown"
BAND_ASKED_FOR = "asked_for"
BANDS = (BAND_YOU_HAVE, BAND_THEY_HAVE, BAND_BOTH, BAND_UNKNOWN, BAND_ASKED_FOR)
BAND_LABELS = {
    BAND_YOU_HAVE: "You have — they don't",
    BAND_THEY_HAVE: "They have — you don't",
    BAND_BOTH: "Both have",
    BAND_UNKNOWN: "Unknown",
    BAND_ASKED_FOR: "Their users ask for it",
}
# The order the four human groups render in (§1); `unknown` is shown too because
# the cell rule requires missing data to be visible, not scored away.
GROUP_ORDER = (BAND_YOU_HAVE, BAND_THEY_HAVE, BAND_BOTH, BAND_UNKNOWN, BAND_ASKED_FOR)

# --- the seven dimensions, in order (docs/gap-table-format.md §2) ----------
DIM_PRICING = "Pricing"
DIM_FREE_TIER = "Free tier"
DIM_FEATURES = "Features"
DIM_POSITIONING = "Positioning / target user"
DIM_DOESNT_DO = "What it doesn't do"
DIM_ACTIVITY = "Activity / liveness"
DIM_ASKS = "What their users ask for"
DIMENSIONS = (DIM_PRICING, DIM_FREE_TIER, DIM_FEATURES, DIM_POSITIONING,
              DIM_DOESNT_DO, DIM_ACTIVITY, DIM_ASKS)

# --- capability-level matching (§2: "markdown" vs "Markdown" is not a row) --
# A small, explicit alias table.  Capabilities are compared at the level of what
# they DO, not how they are spelled: reviewers asking for "offline mode", "work
# without internet" and "local files" are one row.  Kept deliberately short and
# reviewable rather than clever — an unlisted variant simply stays its own row,
# which is the honest failure mode (a spurious merge would hide a real gap).
CAPABILITY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("offline / local files", ("work without internet", "works without internet",
                               "offline access", "offline mode", "local-first",
                               "local first", "local files", "on-device", "offline")),
    ("public API", ("public api", "rest api", "graphql", "developer api",
                    "webhooks", "api access", "api")),
    ("mobile app", ("native app", "android app", "mobile app", "ios app", "mobile")),
    ("real-time collaboration", ("real-time collaboration", "realtime collaboration",
                                 "real time collaboration", "co-editing",
                                 "multiplayer", "collaboration")),
    ("markdown", ("markdown notes", "markdown", "md files")),
    ("sync", ("cloud sync", "device sync", "sync")),
    ("self-host", ("self-hosted", "self-host", "self host", "on-premise",
                   "on-prem", "on prem")),
    ("export", ("data export", "export data", "export")),
    ("plugins", ("plugin ecosystem", "plugins", "extensions", "add-ons", "plugin")),
    ("free tier", ("free plan", "free tier")),
)

_PUNCT = re.compile(r"[^a-z0-9]+")


def _norm(text) -> str:
    """Lowercase, punctuation -> single spaces, collapsed. The comparison key."""
    return _PUNCT.sub(" ", str(text or "").lower()).strip()


def _build_alias_index():
    index: list[tuple[str, str]] = []
    for canonical, members in CAPABILITY_ALIASES:
        for member in members:
            index.append((canonical, _norm(member)))
    # Longest phrases first, so "public api" wins over "api" and "local first"
    # is not shadowed by a shorter neighbour.
    index.sort(key=lambda pair: len(pair[1]), reverse=True)
    return tuple(index)


_ALIAS_INDEX = _build_alias_index()


def canonical_capability(text) -> str:
    """The capability key a feature or an ask is matched on.

    Falls back to the normalized text itself, so an unlisted capability still
    compares against an identically-spelled one (that is the "markdown" ==
    "Markdown" case) without any table entry.
    """
    normalized = _norm(text)
    if not normalized:
        return ""
    for canonical, member in _ALIAS_INDEX:
        if re.search(r"(?<![a-z0-9])" + re.escape(member) + r"(?![a-z0-9])", normalized):
            return canonical
    return normalized


# --- small parsers ---------------------------------------------------------

def parse_features(raw) -> list[str]:
    try:
        data = json.loads(raw) if raw else []
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def parse_pricing(raw) -> dict:
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        return {"free_tier": "", "plans": []}
    plans = [p for p in (data.get("plans") or []) if isinstance(p, dict)]
    return {"free_tier": str(data.get("free_tier") or "").strip(), "plans": plans}


def free_tier_state(text) -> str:
    """yes | no | unknown — the free-tier flag as a claim, never invented."""
    t = _norm(text)
    if not t:
        return "unknown"
    if "no free" in t or "paid only" in t or t.startswith("none") or t in ("no", "paid"):
        return "no"
    return "yes"


def _text(value) -> str:
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def _field(row_obj, key, default=None):
    try:
        return row_obj[key]
    except (KeyError, IndexError, TypeError):
        return default


def _row(dimension: str, band: str, you: str, them: str,
              source: str = "", captured_at: str = "") -> dict:
    """One gap-table row — exactly `{dimension, band, you, them, source,
    captured_at}` (`docs/gap-table-format.md` §5)."""
    return {
        "dimension": dimension,
        "band": band,
        "you": you or "",
        "them": them or "",
        "source": source or "",
        "captured_at": captured_at or "",
    }


# --- slug + resolution (F-17) ----------------------------------------------

def slugify(name) -> str:
    """The documented slug rule (module docstring): lowercase, non-alphanumeric
    runs -> single hyphen, ends trimmed."""
    return _PUNCT.sub("-", str(name or "").lower()).strip("-")


def _ref_field(ref, *keys):
    """Pull a reference out of an int, a str, or a dict of well-known keys."""
    if isinstance(ref, dict):
        for key in keys:
            if ref.get(key) not in (None, ""):
                return ref[key]
        return None
    return ref


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_startup(conn, ref):
    """Resolve a competitor reference (id | numeric slug | name slug) to ONE row.

    Returns the chosen row or None.  Collisions resolve deterministically — the
    human-verified row first, then the lowest id — matching the slug endpoint so
    a comparison and a `/products/<slug>` page agree on which duplicate they mean.
    """
    value = _ref_field(ref, "startup_id", "id", "slug", "name")
    if value is None:
        return None
    as_id = _as_int(value)
    if as_id is not None and not isinstance(value, str):
        # An int ref is an explicit id.
        return conn.execute("SELECT * FROM startups WHERE id = ?", (as_id,)).fetchone()
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (int(text),)).fetchone()
        if row:
            return row
    candidates = _slug_candidates(conn, slugify(text))
    return candidates[0] if candidates else None


def _slug_candidates(conn, slug: str) -> list:
    """Every archive row whose name slugifies to `slug`, best-first.

    Prefiltered by the slug's first token so a normal lookup does not scan the
    whole table, then filtered in Python (slugs drop punctuation, which SQL
    cannot express cheaply).
    """
    if not slug:
        return []
    first = slug.split("-")[0]
    # LIKE is case-insensitive for ASCII; the Python filter below is exact.
    rows = conn.execute(
        "SELECT * FROM startups WHERE lower(name) LIKE ? ESCAPE '\\'",
        (f"%{first}%",),
    ).fetchall()
    matched = [r for r in rows if slugify(r["name"]) == slug]
    # Deterministic collision rule: human-verified first, then the lowest id.
    matched.sort(key=lambda r: (0 if r["verified"] == 1 else 1, r["id"]))
    return matched


def resolve_startup_slug(conn, slug: str):
    """(row, candidates) for the slug endpoint.  A numeric slug is also accepted
    as an id for convenience, after the name-slug lookup misses."""
    candidates = _slug_candidates(conn, slugify(slug))
    if candidates:
        return candidates[0], candidates
    if str(slug).isdigit():
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (int(slug),)).fetchone()
        if row:
            return row, [row]
    return None, []


def founder_ref_to_id(ref):
    """Resolve the `you` reference to a founder_apps id (int | numeric | name
    slug).  Returns None when nothing matches."""
    if ref is None:
        return None
    value = _ref_field(ref, "founder_app_id", "id", "slug", "name")
    if value is None:
        return None
    as_id = _as_int(value)
    if as_id is not None and not isinstance(value, str):
        return founder.get(as_id) and as_id
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text) if founder.get(int(text)) else None
    slug = slugify(text)
    conn = founder.connect()
    try:
        rows = conn.execute("SELECT id, name FROM founder_apps ORDER BY id").fetchall()
    finally:
        conn.close()
    for row in rows:
        if slugify(row["name"]) == slug:
            return int(row["id"])
    return None


# --- trust badges (F-21) ----------------------------------------------------

def badges(row) -> dict:
    """`admin_verified` / `machine_verified` as EXPLICIT fields, never inferred
    by a client from a raw timestamp (F-21, docs/teardown-spec.md §8.1).

    No new columns: Admin Verified is `verified` + `verified_at` (the human
    stamp, the archive's entry gate, never decays); Machine Verified is
    `status` + `last_checked` + `check_failures` (the weekly pass, decays —
    re-earned on every pass).  A stale `last_checked` reads
    `machine_verified=False` while `admin_verified` stays True.
    """
    from . import config  # local import: avoids a config import cycle at module load

    verified = _field(row, "verified", 0)
    verified_at = _field(row, "verified_at")
    status = _field(row, "status")
    last_checked = _field(row, "last_checked")
    failures = _field(row, "check_failures", 0) or 0
    admin = bool(verified)
    # The freshness window is the verify rhythm (7 days).  VERIFY_AUTO_STALE_DAYS
    # is 0 when auto-verify is switched off for a throwaway instance; falling
    # back to CAPTURE_STALE_DAYS there keeps the badge meaningful rather than
    # reading "everything is stale" purely because the scheduler is disabled.
    window = config.VERIFY_AUTO_STALE_DAYS if config.VERIFY_AUTO_STALE_DAYS > 0 \
        else config.CAPTURE_STALE_DAYS
    fresh = capture.age_days(last_checked)
    machine = (
        bool(last_checked)
        and fresh is not None
        and fresh <= window
        and status == "active"
        and failures == 0
    )
    return {
        "admin_verified": admin,
        "admin_verified_at": verified_at,
        "machine_verified": machine,
        "machine_verified_at": last_checked,
    }


def startup_payload(row, candidates=None) -> dict:
    """The `/api/startups/{slug}` row: the archive row plus the slug, the two
    explicit badges, and the duplicate group so a client can tell which row it
    got.  Badges are fields on the RECORD, never on a claim (F-21)."""
    payload = dict(row)
    payload.pop("_inserted", None)
    payload["slug"] = slugify(row["name"])
    payload["resolved_id"] = int(row["id"])
    payload["resolved_name"] = row["name"]
    payload.update(badges(row))
    payload["duplicate_group"] = [
        {"id": int(c["id"]), "name": c["name"], "verified": bool(c["verified"])}
        for c in (candidates or [row])
    ]
    return payload


# --- the two sides, gathered from their two stores -------------------------

def you_side(founder_row) -> dict:
    """The `you` record, read from the founder store in the shape the diff uses.

    Only what the founder entered — the product does not invent the founder's
    features (cell rule 3).
    """
    profile = founder.profile_of(founder_row)
    features: dict[str, str] = {}
    for feat in profile.get("features") or []:
        cap = canonical_capability(feat)
        if cap and cap not in features:
            features[cap] = feat
    pricing = profile.get("pricing") or {}
    if not isinstance(pricing, dict):
        pricing = {}
    return {
        "name": profile.get("name") or f"founder-app-{founder_row['id']}",
        "founder_app_id": int(founder_row["id"]),
        "features": features,
        "pricing": pricing,
        "free_tier": pricing.get("free_tier") or "",
        "positioning": _text(profile.get("positioning")),
        "target_users": _text(profile.get("target_users")),
        "links": {k: profile.get(k) or "" for k in (
            "website_url", "github_url", "app_store_url", "play_store_url")},
    }


def them_side(conn, row) -> dict:
    """One competitor's side, read from the archive row and its evidence rows.

    Every capability a feature row carries is paired with the page it came from;
    when the evidence table has no feature rows (a teardown that predates this
    phase) the stored `features_json` is used with the homepage as its source,
    which is still a source.
    """
    sid = int(row["id"])
    home = _text(row["website_url"])
    ev_rows = ev.for_startup(conn, sid)

    features: dict[str, dict] = {}
    positioning: dict | None = None
    negatives: list[dict] = []
    for r in ev_rows:
        kind = r["evidence_type"]
        source = _text(r["source_url"])
        captured = _text(r["captured_at"])
        if kind == "feature":
            cap = canonical_capability(r["claim"])
            if cap and cap not in features:
                features[cap] = {"text": _text(r["claim"]), "source": source,
                                 "captured_at": captured}
        elif kind == "positioning" and positioning is None:
            positioning = {"text": _text(r["claim"]) or _text(r["value"]),
                           "source": source, "captured_at": captured}
        elif kind == "negative":
            negatives.append({
                "claim": _text(r["claim"]),
                "canonical": canonical_capability(r["claim"]),
                "source": source,
                "captured_at": captured,
                "value": _text(r["value"]),
                "unknown": _text(r["value"]).lower() == "unknown",
            })

    feature_source = home
    feature_captured = _text(_field(row, "pricing_captured_at"))
    if not features:
        for feat in parse_features(_field(row, "features_json")):
            cap = canonical_capability(feat)
            if cap and cap not in features:
                features[cap] = {"text": feat, "source": home, "captured_at": ""}
    if not positioning:
        pos_text = _text(_field(row, "positioning"))
        if pos_text:
            positioning = {"text": pos_text, "source": home, "captured_at": ""}

    pricing = parse_pricing(_field(row, "pricing_json"))
    activity = _activity_text(row)

    return {
        "id": sid,
        "name": row["name"],
        "slug": slugify(row["name"]),
        "website_url": home,
        "home_url": home,
        "features": features,
        "feature_source": feature_source,
        "feature_captured": feature_captured,
        "positioning": positioning,
        "negatives": negatives,
        "pricing": pricing,
        "pricing_source_url": _text(_field(row, "pricing_source_url")),
        "pricing_captured_at": _text(_field(row, "pricing_captured_at")),
        "activity": activity,
        "asks": _asks_for(conn, sid),
        "has_teardown": bool(features or positioning or pricing["plans"]
                             or pricing["free_tier"] or negatives),
    }


def _activity_text(row) -> dict:
    status = _field(row, "status") or "active"
    last_checked = _text(_field(row, "last_checked"))
    failures = _field(row, "check_failures", 0) or 0
    if status in ("dead", "pivoted"):
        text = f"{status} — filed, never deleted"
    elif not last_checked:
        text = "not yet checked"
    else:
        text = f"alive, last checked {last_checked}"
        if failures:
            text += f" ({failures} failed check(s))"
    return {"text": text, "source": _text(row["website_url"]),
            "captured_at": last_checked}


def _asks_for(conn, startup_id: int) -> list[dict]:
    """Dimension 7's input: every ask, with the review it came from.  Read from
    the review evidence rows — never re-fetched, never scored (F-23)."""
    out: list[dict] = []
    for ask in _asks_from_evidence(conn, startup_id):
        text = _text(ask.get("ask"))
        cap = canonical_capability(text)
        if not text or not cap:
            continue
        out.append({"ask": text, "canonical": cap,
                    "source": _text(ask.get("source_url")),
                    "captured_at": _text(ask.get("captured_at"))})
    return out


def _asks_from_evidence(conn, startup_id: int) -> list[dict]:
    from . import reviews  # local import: keeps the module graph one-directional
    return reviews.asks_from_evidence(conn, startup_id)


# --- the diff ---------------------------------------------------------------

def _join(cells: list[str]) -> str:
    seen: list[str] = []
    for cell in cells:
        if cell and cell not in seen:
            seen.append(cell)
    return " · ".join(seen)


def _sources(cells: list[str]) -> str:
    return _join([c for c in cells if c])


def _negatives_by_cap(sides) -> dict:
    """capability -> (negative dict, side) for the first sourced negative."""
    out: dict[str, tuple[dict, dict]] = {}
    for side in sides:
        for neg in side["negatives"]:
            cap = neg["canonical"]
            if not cap or cap in out:
                continue
            out[cap] = (neg, side)
    return out


def build_table(you_row, competitor_rows, conn) -> dict:
    """The whole comparison: two sides, seven dimensions, five bands.

    Returns a dict carrying the band groups, a flat `rows` list in dimension
    order (what the exports walk), and both sides' summaries.
    """
    you = you_side(you_row)
    sides = [them_side(conn, r) for r in competitor_rows]
    rows: list[dict] = []
    rows += _dimension_pricing(you, sides)
    rows += _dimension_free_tier(you, sides)
    rows += _dimension_features(you, sides)
    rows += _dimension_positioning(you, sides)
    rows += _dimension_doesnt_do(you, sides)
    rows += _dimension_activity(you, sides)
    rows += _dimension_asks(you, sides)

    groups = {band: [] for band in BANDS}
    for row in rows:
        groups[row["band"]].append(row)

    payload = {
        "you": {"name": you["name"], "founder_app_id": you["founder_app_id"],
                "profile": {k: v for k, v in you.items() if k != "features"}},
        "them": [
            {"id": s["id"], "name": s["name"], "slug": s["slug"],
             "website_url": s["website_url"], "has_teardown": s["has_teardown"]}
            for s in sides
        ],
        "competitors": [{"id": s["id"], "name": s["name"], "slug": s["slug"]} for s in sides],
        "groups": groups,
        "rows": rows,
        "bands": list(BANDS),
        "dimensions": list(DIMENSIONS),
    }
    # The spec's shape puts the bands at the top level of the response too.
    for band in BANDS:
        payload[band] = groups[band]
    return payload


def _plan_text(plan: dict, side_name: str = "") -> str:
    """One plan rendered as "Name $price/period (competitor)"."""
    out = f"{_text(plan.get('name'))} {_text(plan.get('price'))}".strip()
    period = _text(plan.get("period"))
    if period:
        out += f"/{period}"
    if side_name:
        out += f" ({side_name})"
    return out


def _dimension_pricing(you: dict, sides) -> list[dict]:
    """Plan-by-plan (dim 1): one row per plan name, matched at the name level."""
    you_plans: dict[str, dict] = {}
    for plan in (you["pricing"].get("plans") or []):
        name = _text(plan.get("name"))
        if name:
            you_plans.setdefault(_norm(name), plan)

    them_plans: dict[str, list[tuple[dict, dict]]] = {}
    any_them_pricing = False
    for side in sides:
        plans = side["pricing"].get("plans") or []
        if plans or side["pricing"].get("free_tier"):
            any_them_pricing = True
        for plan in plans:
            name = _text(plan.get("name"))
            if name:
                them_plans.setdefault(_norm(name), []).append((plan, side))

    if not you_plans and not them_plans:
        return [_row(DIM_PRICING, BAND_UNKNOWN, you="no pricing entered",
                     them="pricing captured, no plan rows" if any_them_pricing
                     else "no pricing captured",
                     source="")]

    out: list[dict] = []
    order = list(you_plans) + [k for k in them_plans if k not in you_plans]
    for key in order:
        y = you_plans.get(key)
        t = them_plans.get(key) or []
        y_text = _plan_text(y) if y else "not offered"
        t_text = _join([_plan_text(p, s["name"]) for p, s in t])
        if y and t:
            out.append(_row(DIM_PRICING, BAND_BOTH, you=y_text, them=t_text,
                            source=_sources([s["pricing_source_url"] for _, s in t]),
                            captured_at=_sources([s["pricing_captured_at"] for _, s in t])))
        elif y:
            src = _sources([s["pricing_source_url"] for s in sides if s["has_teardown"]])
            cap = _sources([s["pricing_captured_at"] for s in sides if s["has_teardown"]])
            band = BAND_YOU_HAVE if src else BAND_UNKNOWN
            out.append(_row(DIM_PRICING, band, you=y_text,
                            them="not listed on their pricing page" if src else "unknown",
                            source=src, captured_at=cap))
        else:
            out.append(_row(DIM_PRICING, BAND_THEY_HAVE, you="not offered", them=t_text,
                            source=_sources([s["pricing_source_url"] for _, s in t]),
                            captured_at=_sources([s["pricing_captured_at"] for _, s in t])))
    return out


def _free_tier_for_side(side: dict) -> str:
    """yes | no | unknown for one competitor.

    `no` is only claimed when the pricing page was read (the free-tier line is
    part of that page) or a sourced "no free tier" negative exists — otherwise
    it is `unknown`, never "no".
    """
    state = free_tier_state(side["pricing"].get("free_tier"))
    if state != "unknown":
        return state
    for neg in side["negatives"]:
        if neg["canonical"] == "free tier" and not neg["unknown"] and neg["source"]:
            return "no"
    return "unknown"


def _dimension_free_tier(you: dict, sides) -> list[dict]:
    you_state = free_tier_state(you["free_tier"])
    them_states = [(s, _free_tier_for_side(s)) for s in sides]
    them_yes = [s for s, st in them_states if st == "yes"]
    them_no = [s for s, st in them_states if st == "no"]
    them_unknown = [s for s, st in them_states if st == "unknown"]

    you_text = you["free_tier"] or ("no free tier" if you_state == "no" else
                                    "free tier" if you_state == "yes" else "unknown")
    them_text = _join([f"{st} ({s['name']})" for s, st in them_states])
    src = _sources([s["pricing_source_url"] for s in sides])
    cap = _sources([s["pricing_captured_at"] for s in sides])

    if you_state == "unknown":
        return [_row(DIM_FREE_TIER, BAND_UNKNOWN, you=you_text, them=them_text,
                     source=src, captured_at=cap)]
    if you_state == "yes" and them_yes:
        return [_row(DIM_FREE_TIER, BAND_BOTH, you=you_text, them=them_text,
                     source=src, captured_at=cap)]
    if you_state == "yes" and them_no and not them_unknown:
        return [_row(DIM_FREE_TIER, BAND_YOU_HAVE, you=you_text, them=them_text,
                     source=src, captured_at=cap)]
    if you_state == "no" and them_yes:
        return [_row(DIM_FREE_TIER, BAND_THEY_HAVE, you=you_text, them=them_text,
                     source=src, captured_at=cap)]
    return [_row(DIM_FREE_TIER, BAND_UNKNOWN, you=you_text, them=them_text,
                 source=src, captured_at=cap)]


def _dimension_features(you: dict, sides) -> list[dict]:
    neg_by_cap = _negatives_by_cap(sides)
    order: list[str] = list(you["features"])
    display: dict[str, str] = dict(you["features"])
    for side in sides:
        for cap, rec in side["features"].items():
            if cap not in display:
                display[cap] = rec["text"]
                order.append(cap)

    out: list[dict] = []
    for cap in order:
        you_has = cap in you["features"]
        matches = [(s, s["features"][cap]) for s in sides if cap in s["features"]]
        them_has = bool(matches)
        you_text = you["features"][cap] if you_has else "not offered"
        if you_has and them_has:
            out.append(_row(DIM_FEATURES, BAND_BOTH, you=you_text,
                            them=_join([f"{rec['text']} ({s['name']})" for s, rec in matches]),
                            source=_sources([rec["source"] for _, rec in matches]),
                            captured_at=_sources([rec["captured_at"] for _, rec in matches])))
        elif you_has:
            out.append(_feature_you_only_row(cap, you_text, sides, neg_by_cap))
        elif them_has:
            recs = [(s, rec) for s, rec in matches]
            out.append(_row(DIM_FEATURES, BAND_THEY_HAVE, you="not offered",
                            them=_join([f"{rec['text']} ({s['name']})" for s, rec in recs]),
                            source=_sources([rec["source"] for _, rec in recs]),
                            captured_at=_sources([rec["captured_at"] for _, rec in recs])))
    return out


def _feature_you_only_row(cap: str, you_text: str, sides, neg_by_cap: dict) -> dict:
    """A capability only `you` have — your edge, if the "they don't" half is
    sourced.  A sourced negative wins; otherwise the page their feature list was
    enumerated from is the source; with no teardown at all the row is `unknown`
    (missing data is never scored)."""
    neg = neg_by_cap.get(cap)
    if neg and not neg[0]["unknown"] and neg[0]["source"]:
        n, side = neg
        return _row(DIM_FEATURES, BAND_YOU_HAVE, you=you_text,
                    them=f"no — {n['claim']} ({side['name']})",
                    source=n["source"], captured_at=n["captured_at"])
    sourced = [s for s in sides if s["has_teardown"] and s["feature_source"]]
    if sourced:
        return _row(DIM_FEATURES, BAND_YOU_HAVE, you=you_text,
                    them=_join([f"not in their feature list ({s['name']})" for s in sourced]),
                    source=_sources([s["feature_source"] for s in sourced]),
                    captured_at=_sources([s["feature_captured"] for s in sourced]))
    return _row(DIM_FEATURES, BAND_UNKNOWN, you=you_text, them="unknown — no teardown captured",
                source="")


def _dimension_positioning(you: dict, sides) -> list[dict]:
    you_text = you["positioning"] or you["target_users"] or ""
    them_pos = [(s, s["positioning"]) for s in sides if s["positioning"]]
    if you_text and them_pos:
        return [_row(DIM_POSITIONING, BAND_BOTH, you=you_text,
                     them=_join([f"{p['text']} ({s['name']})" for s, p in them_pos]),
                     source=_sources([p["source"] for _, p in them_pos]),
                     captured_at=_sources([p["captured_at"] for _, p in them_pos]))]
    if you_text:
        sourced = [s for s in sides if s["has_teardown"]]
        return [_row(DIM_POSITIONING, BAND_YOU_HAVE if sourced else BAND_UNKNOWN,
                     you=you_text,
                     them="not captured" if sourced else "unknown",
                     source=_sources([s["home_url"] for s in sourced]))]
    if them_pos:
        return [_row(DIM_POSITIONING, BAND_THEY_HAVE, you="not entered",
                     them=_join([f"{p['text']} ({s['name']})" for s, p in them_pos]),
                     source=_sources([p["source"] for _, p in them_pos]),
                     captured_at=_sources([p["captured_at"] for _, p in them_pos]))]
    return [_row(DIM_POSITIONING, BAND_UNKNOWN, you="not entered", them="not captured",
                 source="")]


def _dimension_doesnt_do(you: dict, sides) -> list[dict]:
    """Dimension 5 — the competitor's negatives, as observations.

    A sourced negative whose capability you DO cover is a real edge
    (`you_have_they_dont`).  A sourced negative neither side covers is parity of
    absence (`both_have`: no differentiation).  A negative with no source, or one
    the capture marked `unknown`, is `unknown` — never "no" (cell rule 2).
    """
    out: list[dict] = []
    for side in sides:
        for neg in side["negatives"]:
            claim = neg["claim"] or "(negative)"
            if neg["unknown"] or not neg["source"]:
                out.append(_row(DIM_DOESNT_DO, BAND_UNKNOWN,
                                you=_you_cover_text(you, neg["canonical"]),
                                them=f"unknown — could not read the page ({side['name']})",
                                source=neg["source"]))
                continue
            covered = neg["canonical"] in you["features"]
            band = BAND_YOU_HAVE if covered else BAND_BOTH
            out.append(_row(DIM_DOESNT_DO, band,
                            you=_you_cover_text(you, neg["canonical"]),
                            them=f"{claim} ({side['name']})",
                            source=neg["source"], captured_at=neg["captured_at"]))
    return out


def _you_cover_text(you: dict, canonical: str) -> str:
    if canonical in you["features"]:
        return f"yes — declared: {you['features'][canonical]}"
    return "n/a — not in your declared features"


def _dimension_activity(you: dict, sides) -> list[dict]:
    """Dimension 6 — the competitor's liveness.  The `you` side has no liveness
    signal of its own (the spec marks it n/a), so the row is `unknown`: missing
    data on a side is shown, never scored."""
    them_text = _join([f"{s['activity']['text']} ({s['name']})" for s in sides])
    return [_row(DIM_ACTIVITY, BAND_UNKNOWN, you="n/a",
                 them=them_text or "no activity data",
                 source=_sources([s["activity"]["source"] for s in sides]),
                 captured_at=_sources([s["activity"]["captured_at"] for s in sides]))]


def _dimension_asks(you: dict, sides) -> list[dict]:
    """Dimension 7 — what their users ask for (F-23 → gap table).

    Every ask links to the review it came from.  An ask your declared features
    already cover is your most valuable row (`you_have_they_dont`); an ask
    neither side covers is `asked_for`, outside the three comparison bands.
    Capability-level: "offline mode" and "work without internet" are one row.
    """
    grouped: dict[str, dict] = {}
    for side in sides:
        for ask in side["asks"]:
            entry = grouped.setdefault(ask["canonical"], {
                "text": ask["ask"], "reviewers": [], "sources": [], "captured": []})
            entry["reviewers"].append(side["name"])
            if ask["source"]:
                entry["sources"].append(ask["source"])
            if ask["captured_at"]:
                entry["captured"].append(ask["captured_at"])

    out: list[dict] = []
    for cap, entry in grouped.items():
        covered = cap in you["features"]
        n = len(entry["reviewers"])
        them = f"no — {n} reviewer(s) asked"
        source = _sources(entry["sources"])
        captured = _sources(entry["captured"])
        if covered:
            out.append(_row(DIM_ASKS, BAND_YOU_HAVE,
                            you=f"yes — declared: {you['features'][cap]}",
                            them=them, source=source, captured_at=captured))
        else:
            out.append(_row(DIM_ASKS, BAND_ASKED_FOR, you="no", them=them,
                            source=source, captured_at=captured))
    return out


# --- exports (F-16, shapes in docs/gap-table-format.md §5) -----------------

def _md_cell(value: str) -> str:
    return _text(value).replace("|", "\\|")


def render_markdown(table: dict, *, title: str | None = None) -> str:
    """The three comparison groups plus the demand group (F-16), with the
    unknown group shown too so missing data is visible rather than scored away."""
    you_name = table["you"]["name"]
    them_names = ", ".join(c["name"] for c in table["competitors"]) or "—"
    lines: list[str] = []
    lines.append(f"# {title or 'Gap table'} — {you_name} vs {them_names}")
    lines.append("")
    lines.append(f"_You: {you_name}. Competitor(s): {them_names}._")
    for band in GROUP_ORDER:
        rows = table["groups"].get(band) or []
        lines.append("")
        lines.append(f"## {BAND_LABELS[band]}")
        lines.append("")
        if not rows:
            lines.append("(none)")
            continue
        lines.append("| Dimension | You | Competitor | Source |")
        lines.append("|---|---|---|---|")
        for row in rows:
            src = _md_cell(row["source"])
            if row["captured_at"]:
                src = f"{src} (captured {row['captured_at']})" if src else f"(captured {row['captured_at']})"
            lines.append(
                f"| {_md_cell(row['dimension'])} | {_md_cell(row['you'])} | "
                f"{_md_cell(row['them'])} | {src} |"
            )
    lines.append("")
    return "\n".join(lines)


def _export_rows(table: dict) -> list[dict]:
    """The flat rows the JSON and CSV exports carry — exactly the five/six keys
    §5 names, in dimension order, band included."""
    return [
        {
            "dimension": row["dimension"],
            "you": row["you"],
            "them": row["them"],
            "source": row["source"],
            "captured_at": row["captured_at"],
            "band": row["band"],
        }
        for row in table["rows"]
    ]


def render_json(table: dict) -> str:
    """`{you, them, rows: [{dimension, you, them, source, band}]}` — re-processable."""
    payload = {
        "you": table["you"],
        "them": table["them"],
        "rows": _export_rows(table),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_csv(table: dict) -> str:
    """One row per gap-table row: `band, dimension, you, them, source_url,
    captured_at`.  `asked_for` appears as a band value like any other."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["band", "dimension", "you", "them", "source_url", "captured_at"])
    for row in _export_rows(table):
        writer.writerow([row["band"], row["dimension"], row["you"], row["them"],
                         row["source"], row["captured_at"]])
    return buf.getvalue()


RENDERERS = {
    "markdown": (render_markdown, "text/markdown; charset=utf-8"),
    "md": (render_markdown, "text/markdown; charset=utf-8"),
    "json": (render_json, "application/json; charset=utf-8"),
    "csv": (render_csv, "text/csv; charset=utf-8"),
}
EXPORT_FORMATS = ("markdown", "json", "csv")


def render(fmt: str, table: dict):
    """(text, media_type) for a format name, or (None, None) if unknown."""
    entry = RENDERERS.get((fmt or "").lower())
    if not entry:
        return None, None
    renderer, media_type = entry
    return renderer(table), media_type
