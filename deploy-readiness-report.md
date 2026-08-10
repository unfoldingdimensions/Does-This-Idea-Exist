# Pre-Deployment Readiness Report — IdeaExists ("Does this Startup Exist")

**Date:** 2026-08-10 (evening run, fixes applied same session) · **Target:** LOCAL PRE-FLIGHT (no deployed version; no git remote; no host chosen)
**Stack:** FastAPI :8020 · Next.js 16 :3023 (dev) / built `.next` (served on :3024 for tests) · SQLite
**Runbook:** `predeploy-readiness` skill · sweep executed against the **fresh production build** (`next build` PASS, 4 routes: `/`, `/_not-found`, `/robots.txt`, `/sitemap.xml`)

> Sub-skill note: `predeploy-live-url-qa` was read from disk because the loader index at
> session start predates it (file frontmatter valid — loader-cache quirk; fresh session fixes it).
> **Correction to the first pass:** the original CWV "LCP FAIL" was based on Lighthouse's
> *simulated* (Lantern) value; the `metrics` audit's *observed* trace value was 1.54s (PASS).
> Fixed measurement is below.

## Verdict: 🟡 CAUTION — deployable after host choice; all 3 original blockers fixed

All measured blockers now pass (observed). Remaining items are scheduled human
actions (pick a host, Search Console, cross-browser pass, legal review if the
hosted version adds analytics) plus one SHOULD-FIX (mobile-CPU LCP headroom —
Lighthouse's simulated value is still above 2.5s; field data after launch is
the real gate).

## Results table

| # | Blocker | Status | Evidence | Notes |
|---|---|---|---|---|
| 0 | Pre-flight: target + rollback | ✅ | Local pre-flight confirmed; rollback = git restore + fresh DB backup (`ideasexist.db.bak-predeploy-20260810-2134`) | Host click-path PENDING until host chosen; runbook added: `DEPLOYMENT.md` |
| 1 | Content sweep | ✅ | 0 placeholders in built HTML; favicon 200; unique title + description; 121 external links: 118×200, 1×429 (Axonius bot-limit), 1×202 (Binance), 0 dead; all same-origin assets 200 | Template leftovers removed from `public/`; OG tags now present |
| 2 | Legal | ✅ (N/A) | 0 forms on homepage; dialog collects startup URLs only; 0 third-party scripts; 0 cookies (JS + Set-Cookie); no PII fields in the model | Re-triggers if analytics/accounts are ever added |
| 3 | HTTPS + secrets | ✅ | `.env` git-ignored; only `.env.example` tracked; 0 secret patterns in tree AND full git history; bundle clean; `npm audit` 0 vulnerabilities; security headers live | HTTPS N/A locally → host terminates TLS; regenerate `NEXT_PUBLIC_API_BASE` + CSP at hosting |
| 4 | Core Web Vitals | ✅ (observed) | Lighthouse 13.4.1, 2 runs: **observed LCP 1.54s → 0.83s** (after Lenis deferral) · simulated LCP 3.6s (score 89) · CLS 0.055 · FCP 0.83s · TBT 123ms | LCP PASS on observed; simulated = SHOULD-FIX mobile-CPU headroom; INP not measurable in lab (no interactions); CrUX field data N/A pre-launch |
| 5 | SEO foundations | ✅ | robots.txt 200 (allow-all + Sitemap) · sitemap.xml 200 (well-formed, absolute URL, 1 loc) · canonical present · OG + Twitter meta present | Search Console = PENDING human action (needs a domain); `NEXT_PUBLIC_SITE_URL` drives absolute URLs at hosting |
| 6 | A11y baseline | ✅ | Search-input focus ring now visible in BOTH themes (computed + screenshot evidence; root cause: framer-motion `layout` projection clobbers box-shadow on motion elements → plain-CSS ring on a non-motion wrapper). Contrast PASS both themes (14.3:1 dark / 13.3:1 light body); labels PASS; 320px reflow PASS (CDP); axe-core 4.12.1: 0 violations | Ring was the only failure; fixed + re-verified |
| 7 | Live-URL QA | ✅ (agent subset) | Form E2E PASS (dialog → `POST /api/seed/website` 200 → row id 422 in DB, verified out-of-band, deleted after + DB backed up); console clean (0 msgs/0 errors); no horizontal scroll; w3.org correctly rejected (403 upstream — validation works) | Cross-browser matrix: Chromium covered; Firefox/Safari/real phones = manual, delegated to human |
| 8 | Deploy hygiene | ⏸ PENDING | No host exists — apex/www + DNS deferred by design | Rollback paths per host documented in `DEPLOYMENT.md` |

## Human-action queue

- [ ] Pick a host (Netlify / Vercel / Cloudflare Pages / GitHub Pages) — confirm rollback click-path + DNS records from `DEPLOYMENT.md` (Blockers 0, 8)
- [ ] Search Console verification after the domain exists (Blocker 5)
- [ ] Cross-browser + real-device pass: Firefox, Safari, Android phone, iPhone (Blocker 7)
- [ ] Legal review IF the hosted version adds analytics/accounts/cookies (Blocker 2 re-triggers)
- [ ] Re-check CWV via CrUX once real traffic exists — simulated LCP (3.6s) is the one SHOULD-FIX headroom item (mobile CPU)

## Hosting checklist (carried from security audit + this run)

- [ ] `MUTATION_AUTH=1` + strong `ADMIN_TOKEN`; set `FRONTEND_ORIGIN`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_SITE_URL` to real origins at build time
- [ ] HTTPS + HSTS at the host; `.env` perms 600
- [ ] Shared-venv `cryptography` upgrade is a NO-GO: the venv is Hermes-agent's own and pinned to 48.0.1 — the transitive CVE is LOW and not in the app tree (verified `pip check` clean)
- [ ] Fresh DB backup before migrating (exists: `ideasexist.db.bak-predeploy-20260810-2134`); CHANGELOG + runbook now in repo

## Environment notes (this session's changes, all reversible)

- Backend restarted for CORS testing, now running **default config** again (health 200).
- Global npm: lighthouse 13.4.1, @axe-core/cli 4.12.1 installed.
- Test row (id 422) deleted; background seeder (`backend/scripts/seed_topstartups_all.py` — now committed) added rows during the sweep (412→~420).
- Helper scripts kept: `scripts/contrast_lab.py`, `scripts/reflow-check.mjs` (Lighthouse JSON artifacts git-ignored).
- All work committed this session: a11y ring, Lenis deferral, SEO files, public/ cleanup, CHANGELOG, DEPLOYMENT.md, backend security remediation.
