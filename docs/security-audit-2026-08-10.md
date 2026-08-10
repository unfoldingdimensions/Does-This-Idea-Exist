# Security Audit — IdeaExists ("Does this Startup Exist")

**Date:** 2026-08-10 · **Scope:** full authorized assessment of the owner's own site
**Stack:** FastAPI backend `:8020` (127.0.0.1) · Next.js 16 frontend `:3023` (0.0.0.0) · SQLite · LLM via opencode.go (deepseek-v4-flash)
**Method:** code audit (all 7 backend modules + frontend) · live API testing · supply-chain audit · header/client-side review · secrets & git-history check

---

## Executive summary

The app is in **good shape for a local-first tool**: SQL is fully parameterized (no SQLi), the admin gate uses `hmac.compare_digest` (constant-time), CORS is locked to one origin, the frontend has zero `dangerouslySetInnerHTML`/`eval` sinks (React-escaped rendering), npm audit is clean, and **no secrets were ever committed to git**. The findings below are about the *trust layer* (unauthenticated mutations), the *seed pipeline* (SSRF), and *hosting posture* (headers, binding, rate limits) — the exact things that matter the day this moves past `localhost`.

**Live-proven findings:** SSRF (internal fetch executed), unauthenticated status flip (verify/unverify executed on a real row, since restored), zero rate limiting (15/15 requests passed).

---

## Findings

### HIGH

#### H1 — SSRF via `/api/seed/website` (unauthenticated)
`backend/app/website.py:63` `fetch_homepage()` fetches an **arbitrary URL server-side** with `follow_redirects=True`, no private/loopback/link-local IP blocklist, no redirect-target validation, and no response-size cap. The endpoint `POST /api/seed/website` (`main.py:191`) requires **no auth**.

**Live proof:**
```
curl -X POST http://localhost:8020/api/seed/website -H "Content-Type: application/json" \
  -d '{"website_url":"http://127.0.0.1:8020/api/nonexistent-probe"}'
→ {"detail":"Website unreachable (HTTP 404): http://127.0.0.1:8020/api/nonexistent-probe"}
```
The backend made an outbound request to an internal address and reflected the outcome (also leaks the internal URL in the error).

**Impact when hosted:** hit cloud metadata (`169.254.169.254`), probe internal services, port-scan from the server's network, and burn the owner's **LLM quota + GITHUB_TOKEN rate limit** (seed flow calls the LLM and GitHub API with the owner's credentials — no auth required). Locally: any process on this machine can do the same, plus a `website_url` seeded this way gets fetched again by every verify pass (`verify.py:28` `check_url_ok` — same SSRF class).

**Fix:** private-IP/loopback/link-local blocklist on the *resolved* IP **and** every redirect hop; http(s)-only (already implied); response-size cap (e.g. 2 MB). One shared helper used by `fetch_homepage` and `check_url_ok`.

#### H2 — Unauthenticated data-integrity endpoints (trust-layer bypass)
`main.py:228/250/268` — `POST /api/startups/{id}/verify|unverify|dead` have **no auth**. The product's core promise ("human gate, verification is a real human check") can be silently overwritten by anyone who can reach :8020. Also `POST /api/seed/github`, `/api/seed/website`, `/api/verify/run` are unauthenticated.

**Live proof (row restored afterwards):**
```
curl -X POST http://localhost:8020/api/startups/229/verify     → 200, verified=1   (no token!)
curl -X POST http://localhost:8020/api/startups/229/unverify   → 200, verified=0   (no token!)
```

**Impact:** flips verified/dead status at will (corrupts the "verified by a human" paper trail); triggers expensive seed/verify jobs without permission.

**Fix (additive, keeps current local UX):** new env flag `MUTATION_AUTH=1` (default off = today's behavior). When on, all mutation endpoints require the same `X-Admin-Token` as the admin router. Document that **hosting must set it**. Rate-limit the admin gate too (see M2).

### MEDIUM

#### M1 — No rate limiting anywhere
15 rapid requests → 15× `200`, no 429 anywhere. The `ADMIN_TOKEN` gate has no throttle, so a short/weak token is brute-forceable by anything on the machine (and remotely once hosted). **Fix:** tiny in-memory sliding-window limiter (stdlib only) on admin check + all mutating endpoints; unlimited public GETs stay unlimited.

#### M2 — Frontend dev server bound to `0.0.0.0:3023`
`netstat`: `0.0.0.0:3023 LISTENING`. Any LAN device can load the app and hit the Next dev server (no production protections, webpack HMR surface). API_BASE is `localhost:8020` client-side, so LAN visitors get a broken page anyway — exposure with no benefit. **Fix:** `next dev … -H 127.0.0.1` (one line).

#### M3 — No security headers on either server
- Frontend (`curl -sI :3023`): `X-Powered-By: Next.js`, **no** CSP / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / HSTS / Permissions-Policy.
- Backend: `server: uvicorn` banner, same absence.
**Fix:** `headers()` in `next.config.ts` (CSP production-strict, `frame-ancestors 'none'`, `nosniff`, `no-referrer`, `Permissions-Policy`), plus a tiny middleware for the API. Banners: disable `X-Powered-By` in Next config.

#### M4 — `/api/health` leaks internals
Returns absolute DB path (`E:\New-Personal-Projects\…\backend\data\ideasexist.db`), LLM model, and whether the API key is configured. **Fix:** drop the path (or emit basename only) and the key-configured flag.

### LOW

- **L1 — LLM prompt-injection surface + unvalidated output** (`llm.py`, `enrich.py`): attacker-controlled homepage text/GitHub description is pasted into the LLM prompt; output `name/tagline/description/category/founded` is stored with only `str()` coercion — no length caps, category free-text. Risk = junk/poisoned rows (no XSS — React escapes). **Fix:** caps (name ≤120, tagline ≤300, description ≤4000), category whitelist → `other`.
- **L2 — Admin token in `sessionStorage`** (`lib/api.ts:94`): readable by any same-origin XSS (none today), no expiry/rotation. Acceptable locally; revisit at hosting.
- **L3 — Verify-job status endpoints unauthenticated** (`/api/verify/status/{id}`, `/api/verify/current`): leak job progress/URLs/error strings. Low value to gate; noted.
- **L4 — `backend/.env` `-rw-r--r--`**: world-readable mode on a single-user Windows box — cosmetic here, tighten at hosting.
- **L5 — `cryptography 48.0.1` (3 CVEs, PYSEC-2026-3552/3553/3554, fix ≥49.0.0)**: **transitive in the shared venv** (hermes-agent), **not** in the app's `requirements.txt` tree — no app exposure; upgrade the env when convenient.

---

## What's already solid ✅

- No SQLi — every query parameterized (`main.py`, `db.py`, `seeder.py`, `verify.py`).
- Admin gate: `hmac.compare_digest`, fails loud with 403, disabled when `ADMIN_TOKEN` empty. Live-tested: no-token seed → 403.
- CORS: `allow_origins=[FRONTEND_ORIGIN]` only; evil-origin preflight → no `Access-Control-Allow-Origin` (blocked), allowed origin → echoed correctly.
- Frontend: no `dangerouslySetInnerHTML`/`innerHTML`/`eval`/`new Function` anywhere; stored URLs always http(s) (backend-validated); external links `target="_blank" rel="noreferrer"`.
- Supply chain: `npm audit` 0 vulns; `pip check` clean; `requirements.txt` minimal (4 packages).
- Secrets: `backend/.env` git-ignored, **never in git history**; `.env.example` placeholders only.
- Jobs are kind-scoped/serialized; verify never deletes; failures are loud.

---

## Evidence log (reproducible)

```
# SSRF (H1)
curl -X POST http://localhost:8020/api/seed/website -H "Content-Type: application/json" -d '{"website_url":"http://127.0.0.1:8020/api/nonexistent-probe"}'
# Unauth status flip (H2)
curl -X POST http://localhost:8020/api/startups/229/verify
curl -X POST http://localhost:8020/api/startups/229/unverify
# No rate limit (M1)
for i in $(seq 1 15); do curl -s -o /dev/null -w "%{http_code} " http://localhost:8020/api/startups; done
# Headers (M3)
curl -sI http://localhost:3023 ; curl -sI http://localhost:8020/api/health
# Admin gate (positive)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8020/api/admin/check   → 403
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8020/api/admin/seed -H "Content-Type: application/json" -d '{"source":"famous","params":{"cap":1}}' → 403
# CORS (positive)
curl -s -i -X OPTIONS http://localhost:8020/api/startups -H "Origin: http://evil.example" -H "Access-Control-Request-Method: GET" | grep -i access-control
# Supply chain
cd frontend && npm audit           → 0 vulnerabilities
cd backend && .venv/Scripts/python -m pip_audit   → cryptography 48.0.1 (transitive, see L5)
```

**Note:** the H2 live test flipped row 229 (996.ICU) to verified and back; original `verified_at` was not recoverable (row predates the 01:50 backup) — restored to `verified=1, verified_at=NULL`. Re-stamp it via the status pill if you want today's date on record.

---

## Remediation (implemented 2026-08-10, all additive)

| Finding | Fix | Verification |
|---------|-----|--------------|
| H1 SSRF | New `backend/app/netguard.py` — `safe_get()` blocks non-public targets on the **resolved IP of every hop** (hostname + private/loopback/link-local/CGNAT/reserved, IPv4+IPv6), 2 MB body cap, 5-redirect limit. Wired into `website.fetch_homepage` and `verify.check_url_ok`. | `127.0.0.1`, `localhost`, `[::1]`, `169.254.169.254`, `192.168.1.1`, `10.0.0.1` → all **400 blocked**; `https://example.com` → 200 ✅ |
| H2 unauth mutations | New `MUTATION_AUTH` env flag (default **off** = today's local UX). On: status-flip / seed / verify-run endpoints demand `X-Admin-Token`. Frontend `markVerified/markUnverified/markDead` now send the token when unlocked (additive). | Isolated :8021 instance with `MUTATION_AUTH=1`: every mutation → **403** without token ✅ |
| M1 no rate limits | (a) per-IP failed-auth lockout **inside `require_admin`** (10 fails/min → 429) — brute-force throttled, legit usage never throttled; (b) per-IP sliding-window limiter on admin check (20/min), admin seed (20/min), seed URLs (20/min), verify/run (10/min), status flips + approve (60/min). `RATE_LIMIT_ENABLED=0` disables. | 15 rapid no-token admin/check → 10× 403 then **5× 429** ✅; 25 token-valid admin/check → 20× 200 then 5× 429 ✅ |
| M2 frontend on 0.0.0.0 | `next dev … -H 127.0.0.1` in `package.json` | netstat: **127.0.0.1:3023 only** ✅ |
| M3 no security headers | `next.config.ts` `headers()` (nosniff, frame-deny, no-referrer, Permissions-Policy always; **strict CSP in production** — `script-src 'self' 'unsafe-inline'` because Next 16 inlines the RSC bootstrap; nonce-based strict policy is the hosting-time upgrade) + `poweredByHeader: false`; backend middleware adds the same headers to every API response. | Headers present on both servers; `X-Powered-By` gone ✅ |
| M4 health leak | `/api/health` now returns `db` basename only; dropped `llm_configured` (frontend never used it). | `{"ok":true,"llm_model":"deepseek-v4-flash","db":"ideasexist.db"}` ✅ |
| L1 LLM output | `_clean_profile()` in `enrich.py`: name ≤120 / tagline ≤300 / description ≤4000, category whitelist → `other`. | Smoke suite numeric-coercion test still passes ✅ |

**Regression gates:** backend smoke **58/58 PASS** · frontend `npm run lint && next build` PASS · live SSRF/flip/header/CORS re-tests PASS · both servers restarted with the new code (no active jobs at restart; 1 stale interrupted job recovered honestly by design).

**Left as documented (hosting-time):** L2 sessionStorage token (revisit with HttpOnly cookie + expiry at hosting), L3 verify-status endpoints (read-only), L5 `cryptography` 48.0.1 CVEs (transitive in the shared venv, not in `requirements.txt` — upgrade the venv: `pip install -U "cryptography>=49.0.0"` when convenient).

**Hosting checklist (README-worth):** set `MUTATION_AUTH=1` + a strong `ADMIN_TOKEN`, set `FRONTEND_ORIGIN` to the real origin, regenerate `NEXT_PUBLIC_API_BASE` + CSP `connect-src` to match, serve behind HTTPS with HSTS, and tighten `.env` perms.

Artifacts: `backend/scripts/verify_fixes.py` (re-runnable fix verification against a test instance).
