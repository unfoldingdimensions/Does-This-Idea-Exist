# Website / GitHub Brand Icons — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Give every startup card/detail a real brand icon (site favicon / GitHub owner avatar) fetched server-side at seed time, stored locally, and served from the app — replacing the hue-initials avatar as primary identity with hue initials as the fallback.

**Architecture:** Icon capture rides the *existing* seed fetches (homepage HTML + GitHub API payload are already downloaded during `_ingest`; no new network surface). Icons are stored in a separate `startup_icons` table (BLOB + mime + fetched_at) so the startups list JSON stays lean. A new `GET /api/startups/{id}/icon` route serves bytes with caching headers; the list API gains a `has_icon` boolean. Frontend `HueAvatar` renders `<img>` when `has_icon`, else the current hue initials — same rounded-md chip in both themes.

**Tech Stack:** Python 3.11 stdlib (`sqlite3`, `html.parser`), FastAPI, httpx; Next.js 16 + motion/react frontend. No new dependencies (raster-only icons — no Pillow needed).

**Privacy stance (must be re-confirmed — see Open Questions):** Icons are fetched *by the backend at seed time* (same moment it already fetches the homepage/repo) and stored locally; the browser never contacts a third party. This **preserves** the documented "no favicon fetching (privacy)" posture (PRODUCT.md:38, :60) — the old rule's intent was no third-party icon CDNs leaking browsing to Google/DDG/Clearbit. The doc wording gets a carve-out, like The Sky did.

---

## Current Context

- `enrich.seed_from_github()` → `gh.fetch_repo()` already downloads the full repo JSON (which includes `owner.avatar_url` — currently discarded).
- `enrich.seed_from_website()` → `ws.fetch_homepage()` already downloads the full homepage HTML (`r.text` — currently only title/meta/text are kept; raw HTML is dropped).
- `db.SCHEMA` is "additive changes only" (v1); a new `startup_icons` table fits that rule. `SELECT *` on startups stays untouched → no JSON bloat.
- `HueAvatar` (frontend/components/hue-avatar.tsx) is the single avatar component used in startup-card, startup-detail header, and "More like this" rows — one upgrade point.
- Startup type (frontend/lib/types.ts) has no icon field yet; `main.py` `list_startups` returns `dict(row)` per row.
- Admin seeder is now a **serial queue** (`seeder.py`) — a backfill job must use the same queue (no parallel seeding).

## Proposed Approach

**Source priority:**
1. **GitHub-backed startups:** `owner.avatar_url` from the existing repo API call → rewrite size param to `s=64` → download → store.
2. **Website-backed startups:** parse homepage HTML for `<link rel="icon">` / `apple-touch-icon` / `shortcut icon` (in that priority — apple-touch is highest quality), resolve relative URL; fallback to `https://{host}/favicon.ico`.
3. **None found / fetch fails / not an allowed raster type / >256KB:** no icon → hue initials fallback. Icon failure **never** fails the seed (best-effort, logged).

**Storage:** `startup_icons(startup_id INTEGER PRIMARY KEY, mime TEXT, data BLOB, fetched_at TEXT)` — single backup unit with the DB, no filesystem management.

**Serving:** `GET /api/startups/{id}/icon` → `Response(data, media_type=mime)` + `Cache-Control: max-age=86400` + `X-Content-Type-Options: nosniff` (mimes restricted to `image/png|jpeg|webp|ico|gif` — **SVG rejected** to avoid the stored-XSS vector of serving arbitrary SVG). Raster-only also avoids Pillow.

**Frontend:** `has_icon` from the API; `HueAvatar` takes an optional `iconUrl`; renders `<img src="/api/startups/{id}/icon">` inside the existing chip (white/`bg-muted` chip so transparent favicons read on charcoal) with `onError` → fallback to initials (handles a deleted/empty icon without a round-trip). `HueAvatar` stays the same size/shape → zero layout churn.

**Backfill:** existing 247 entries get icons via a new admin "Fetch missing icons" job that enqueues on the **serial** queue (runs after any running seed; never parallel). It iterates startups where `startup_icons` is empty, re-uses existing stored homepage HTML where available, and only network-fetches what's missing.

---

## Step-by-Step Plan

### Task 1: Backend — `startup_icons` table + icon helpers

**Objective:** Schema + a `icons.py` module with extraction/storage helpers, fully unit-tested.

**Files:**
- Modify: `backend/app/db.py` (SCHEMA — add table)
- Create: `backend/app/icons.py`
- Create: `backend/tests/test_icons.py`

**Step 1: Add table to SCHEMA** (`db.py`)
```sql
CREATE TABLE IF NOT EXISTS startup_icons (
  startup_id INTEGER PRIMARY KEY,
  mime TEXT NOT NULL,
  data BLOB NOT NULL,
  fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Step 2: Write failing tests** (`backend/tests/test_icons.py`, run with `python -m pytest` if available else extend smoke)
- `extract_icon_url(html)` returns `apple-touch-icon` href over `icon` over `shortcut icon`; handles `href`/`content` ordering; relative URLs resolved against page URL.
- `allowed_mime("image/svg+xml")` → False; png/jpeg/webp/ico/gif → True.
- `save_icon(conn, startup_id, mime, data)` upserts; `get_icon(conn, startup_id)` returns row or None; `has_icon(conn)` joins cleanly.
- Oversize (>256KB) rejected.

**Step 3: Implement** `icons.py`
- `extract_icon_url(html: str, page_url: str) -> str | None`
- `fetch_icon(url: str) -> tuple[mime, bytes] | None` — httpx GET with UA_BROWSER, 15s timeout, size cap 256KB, content-type allowlist, follow_redirects.
- `save_icon(conn, startup_id, mime, data)`, `get_icon(conn, startup_id)`, `clear_icon(conn, startup_id)`.
- `ALLOWED_MIMES` + `MAX_ICON_BYTES` constants.

**Step 4: Run tests → PASS. Commit** (`feat: icon storage + extraction helpers`)

### Task 2: Backend — capture icons during seeding (both paths + API route)

**Objective:** GitHub + website seeds store icons automatically; icon served via API; `has_icon` in the startups list.

**Files:**
- Modify: `backend/app/github.py` (`fetch_repo` — return `owner_avatar_url`)
- Modify: `backend/app/website.py` (`fetch_homepage` — return raw `html`)
- Modify: `backend/app/enrich.py` (`seed_from_github` / `seed_from_website` — call icons helpers after upsert)
- Modify: `backend/app/main.py` (`list_startups` — add `has_icon`; new `GET /api/startups/{id}/icon`)

**Step 1: Extend fetchers**
- `github.py`: `"owner_avatar_url": (d.get("owner") or {}).get("avatar_url")` — free, already in the payload. When fetching, rewrite query to `s=64`.
- `website.py`: add `"html": text` to the returned dict (already in memory — no extra request).

**Step 2: enrich.py — store icon after upsert (best-effort)**
```python
try:
    icons.save_from_seed(conn, row, github_avatar_url=..., html=..., page_url=...)
except Exception:
    log.warning(...)  # never fails the seed
```
Place after `_upsert` in both seed functions (reuse_profile path refreshes the icon too).

**Step 3: main.py**
- `list_startups`: `SELECT s.*, (i.startup_id IS NOT NULL) AS has_icon FROM startups s LEFT JOIN startup_icons i ON i.startup_id = s.id` (keep existing WHERE/ORDER).
- New route:
```python
@app.get("/api/startups/{startup_id}/icon")
def startup_icon(startup_id: int):
    row = icons.get_icon(db.connect(), startup_id)
    if not row: raise HTTPException(404, "No icon")
    return Response(row["data"], media_type=row["mime"],
                    headers={"Cache-Control": "max-age=86400", "X-Content-Type-Options": "nosniff"})
```

**Step 4: Extend smoke tests** (`backend/tests/smoke.py`)
- Fake homepage returns HTML with `<link rel="icon" href="https://x/favicon.png">` → seed → `has_icon == 1`, `/icon` returns bytes with `image/png`.
- Fake github repo returns `owner.avatar_url` → icon stored.
- No icon → `has_icon == 0`, `/icon` → 404.

**Step 5: `npm test` + detector → PASS. Commit** (`feat: seed-time icon capture + serve endpoint`)

### Task 3: Frontend — `HueAvatar` renders brand icons with fallback

**Objective:** Cards, detail modal, and "More like this" show real icons; hue initials remain the fallback; both themes verified.

**Files:**
- Modify: `frontend/lib/types.ts` (`Startup` — add `has_icon: boolean`)
- Modify: `frontend/components/hue-avatar.tsx` (accept `iconUrl?`, render `<img>` on a `bg-muted` chip with `onError` fallback)
- Modify: `frontend/app/page.tsx` (no change needed if `has_icon` flows through `Startup` type — verify)
- Modify: `frontend/components/startup-card.tsx` + `startup-detail.tsx` (pass `iconUrl` where HueAvatar is used)

**Step 1: Type** — `has_icon: boolean` on `Startup`.

**Step 2: HueAvatar**
```tsx
export function HueAvatar({ name, size = "md", iconUrl, className }) {
  const [failed, setFailed] = React.useState(false);
  const icon = iconUrl && !failed ? iconUrl : null;
  return (
    <Avatar aria-label={name} role="img" className={cn("shrink-0 rounded-md", chipSizes, className)}>
      {icon ? (
        <img src={icon} alt="" onError={() => setFailed(true)} className="size-full rounded-md object-cover bg-muted" />
      ) : (
        <AvatarFallback className="rounded-md font-bold" style={hueAvatarStyle(name)}>{initials(name)}</AvatarFallback>
      )}
    </Avatar>
  );
}
```
Chip keeps `bg-muted` so transparent favicons read on charcoal (dark) and beige (light); no hardcoded colors (detector discipline).

**Step 3: Wire iconUrl** — `iconUrl={s.has_icon ? `/api/startups/${s.id}/icon` : undefined}` at all three HueAvatar call sites.

**Step 4: Verify live in browser** — cards, detail header, more-like-this rows show icons; force `onError` (delete an icon) → initials fallback; both themes screenshot; detector `[]`; `npm test` ALL PASS. **Commit** (`feat: brand icons in avatar chips`)

### Task 4: Backend — admin "Fetch missing icons" backfill job

**Objective:** Existing 247 entries get icons, through the serial queue (no parallel seeding).

**Files:**
- Modify: `backend/app/seeder.py` (new `icon_backfill` source producing existing startup ids; `_ingest` special-case for the backfill)
- Modify: `backend/app/main.py` (`POST /api/admin/seed` accepts `source: "icon_backfill"`)
- Modify: `frontend/components/admin-panel.tsx` (add a "Fetch missing icons" action button + source tab)

**Step 1: Backfill source** — yields `(id)` for every startup with no icon row; `_ingest` routes it to a `refresh_icon(startup_id)` that reuses stored homepage HTML when the row has it (or refetches via existing fetchers). Serial queue means it waits behind any running seed.

**Step 2: Admin panel** — "Fetch missing icons" button (uses the same queue + progress sections, no new UI pattern).

**Step 3: Smoke test** — backfill enqueues, drains serially, populates icons for previously icon-less fake rows.

**Step 4: Run backfill once against the live DB** — verify icon coverage % in browser. **Commit** (`feat: admin icon backfill`)

### Task 5: Docs + constraint carve-out

**Files:**
- Modify: `PRODUCT.md` (:38 "no favicon fetching" → carve-out wording; :60 same)
- Modify: `DESIGN.md` (Hue Avatar section: brand icon primary + initials fallback; the "one icon set (lucide)" rule gets a content-vs-chrome carve-out like The Sky)

**Step 1: Write the carve-out** — icons are *content* fetched server-side at seed time, stored locally, never a third-party request at view time; the privacy posture (no tracking, searches stay on machine) is unchanged.

**Step 2: Commit** (`docs: icon feature + privacy carve-out`)

---

## Files Likely to Change

| File | Change |
|---|---|
| `backend/app/db.py` | +`startup_icons` table |
| `backend/app/icons.py` | NEW — extract/fetch/save/serve helpers |
| `backend/app/github.py` | +`owner_avatar_url` in fetch_repo |
| `backend/app/website.py` | +raw `html` in fetch_homepage |
| `backend/app/enrich.py` | store icon after upsert (both paths) |
| `backend/app/main.py` | +`has_icon` in list; +`/api/startups/{id}/icon`; +backfill source |
| `backend/app/seeder.py` | +`icon_backfill` source |
| `backend/tests/smoke.py` | icon capture/serve/backfill checks |
| `backend/tests/test_icons.py` | NEW unit tests |
| `frontend/lib/types.ts` | +`has_icon` |
| `frontend/components/hue-avatar.tsx` | img + initials fallback |
| `frontend/components/startup-card.tsx` | pass `iconUrl` |
| `frontend/components/startup-detail.tsx` | pass `iconUrl` |
| `frontend/components/admin-panel.tsx` | "Fetch missing icons" |
| `PRODUCT.md`, `DESIGN.md` | privacy carve-out |

## Tests / Validation

- `python -m tests.smoke` — all existing + new icon checks PASS (throwaway DB).
- `npm test` — backend smoke + frontend lint/build ALL PASS.
- Detector (`detect.mjs --json`) → `[]` on all touched files.
- Live browser: cards/detail/more-like-this show icons in both themes; onError fallback; backfill improves coverage; no console errors.

## Risks / Tradeoffs

- **Privacy carve-out is the headline risk** — it reverses documented wording ("no favicon fetching"). The *behavior* is preserved (no third-party requests at view time, icons fetched by the backend that already fetches the same site) but the doc must be updated with user sign-off (Open Question 1).
- **Favicon quality varies wildly** — some are 16px blurry, some transparent-on-white, some SVG-only (rejected). The `bg-muted` chip + apple-touch priority + raster-only mitigates; hue initials remain the dignified fallback.
- **Icon fetch latency** — adds ~0.5–2s per *new* website seed (small GET + parse). Falls inside the existing seed job, so the serial queue absorbs it; the 256KB cap bounds worst case. Backfill is a separate queue job, not a page-load path.
- **Bot-blocked favicon paths** — some sites 403 `/favicon.ico`; fallback chain + best-effort logging means coverage is "as good as the sites allow".
- **DB grows** — ~2–30KB per icon × 250 entries ≈ few MB; trivial for SQLite, single backup unit.
- **SVG rejection** — deliberately drops some sites' only icon (XSS hygiene) — documented tradeoff.

## Open Questions (defaults chosen — confirm or override)

1. **Privacy model** — *Default: server-side fetch at seed time, store locally, serve from app* (preserves the documented posture; no third-party requests at view time). **Alternative (not recommended): third-party icon CDN** (Google favicons / DuckDuckGo / Clearbit) — instant coverage but leaks every card view to that provider and *reverses* the documented privacy stance. **Which do you want?**
2. **GitHub repos use the owner avatar** (org/user profile picture) as the repo's icon — *Default: yes* (it's the standard visual identity for a repo; zero extra requests since the API already returns it). Alternative: repo OG image (heavier, often absent). OK?
3. **Icon chip background** — *Default: keep the `bg-muted` chip* (current avatar chip) so transparent favicons read on both charcoal and beige. Alternative: white chip always. Which?
4. **Backfill existing 247 entries now?** — *Default: yes*, via the serial admin queue ("Fetch missing icons" button). It re-fetches homepage HTML for icon-less website entries (roughly one extra fetch per entry, throttled). OK?
5. **Where icons appear** — *Default: everywhere HueAvatar renders today* (cards, detail header, more-like-this rows). Anywhere else you want them (e.g. "Just added" hero rows)?

---

## Execution Handoff

Plan complete. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed, or adjust the open questions first?
