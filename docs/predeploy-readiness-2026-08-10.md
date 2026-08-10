# Pre-Deployment Readiness Report — IdeaExists

**Date:** 2026-08-10 · **Scope:** LOCAL version only (no deployed version exists; no git remote)
**Stack:** FastAPI :8020 · Next.js 16 :3023 · SQLite (367 rows, 316 verified, checked 2026-08-10 09:11)

## Verdict: 🟡 CAUTION — locally ready; host with the listed pre-deploy items

No blockers (no critical vulns, no committed secrets, tests pass). The cautions are
commit/deploy hygiene — none block local use.

---

### Passing ✅
- **Tests** — `npm run test` (root): backend smoke 58/58 PASS · frontend `lint` + `next build` PASS
- **No debug code** — zero `console.log/debugger` in app code, zero `print/pdb` in backend app code
- **Dependencies** — `npm audit`: 0 vulnerabilities · `pip check` clean · `requirements.txt` minimal (4 pkgs)
- **Secrets** — only `backend/.env.example` tracked; `backend/.env` git-ignored; no token patterns in tracked files (re-verified)
- **Security hardening** — full audit + remediation applied & live-verified this session (SSRF guard, failed-auth lockout, rate limits, MUTATION_AUTH flag, security headers, slim health); report: `docs/security-audit-2026-08-10.md`
- **Docs** — README (68), PRODUCT.md (73), DESIGN.md (249), research memos, security audit in `docs/`
- **Live health** — backend :8020 200 · frontend :3023 200 · DB fresh (last_checked today) · archive healthy (367 rows, 0 dead)

### Warnings ⚠️ (should fix, won't block local)
1. **13 uncommitted changes** — the entire security remediation is uncommitted (8 modified + 3 new + report). Commit before any deploy.
2. **No CHANGELOG.md** — add one with an `Unreleased` section before the first release/deploy.
3. **Stale DB backup** — `ideasexist.db.bak-20260810` (01:50, 53 KB) vs live DB (20:56, 356 KB). Take a **fresh backup before any deployment** (product principle: "DB backups before merges").
4. **No CI, no remote, no tags** — nothing automates the gate today; `gh` CLI not installed. Fine for local; needed for hosted.
5. **Dev-dep majors behind** — eslint 9→10, TypeScript 5→7, @types/node 20→26 (runtime deps all current; not blockers).

### N/A (no deployed version)
- Version bump vs tag (0 tags — first release would be v0.1.0)
- CI status / branch sync (no remote)

### Hosting checklist (when you do deploy — from the security audit)
- [ ] Set `MUTATION_AUTH=1` + strong `ADMIN_TOKEN` in the host env
- [ ] Set `FRONTEND_ORIGIN` to the real origin; regenerate `NEXT_PUBLIC_API_BASE` + CSP `connect-src` to match
- [ ] Serve behind HTTPS + HSTS (CSP is production-gated in `next.config.ts`)
- [ ] Tighten `.env` perms (600)
- [ ] Upgrade shared venv `cryptography>=49.0.0` (transitive CVE, not in app tree)
- [ ] Add a release/rollback runbook + DB backup before the migration

### Other
- Untracked `backend/scripts/seed_topstartups_all.py` — not part of this session's work; confirm it's intended and commit or ignore it.
