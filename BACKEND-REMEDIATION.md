# Backend remediation notes

Findings from the 2026-08-18 production-readiness review. The frontend and
design fixes from the same review are already implemented; the backend items
below were **deferred by decision** and need their own session. Ordered by
severity. All line references are against `backend/app/` at commit time and
may drift.

## Critical

### C1 — Verify pass overwrites human status changes made mid-pass

`verify.py:~214` snapshots the whole table once (`SELECT * FROM startups`),
then walks it for minutes (one network check per row). At `verify.py:299-302`
it writes back `check_failures` and `status` **computed from the snapshot**:

```sql
UPDATE startups SET check_failures = ?, last_checked = datetime('now'), status = ? WHERE id = ?
```

Any human action during the pass is silently clobbered when the pass reaches
that row:

- curator files a row **dead** mid-pass → the snapshot's `status='active'`
  gets written back, un-filing it with no log;
- curator **revives** a dead row (`POST /api/startups/{id}/verify` sets
  `status='active', check_failures=0`) → the snapshot's `status='dead'` and
  strike count are restored, undoing the revival.

This violates the app's core invariant ("human judgment outranks
automation") and the weekly pass runs **unattended**, so the window is
realistic.

**Fix sketch:** optimistic concurrency — make the UPDATE conditional
(`WHERE id = ? AND check_failures = ? AND status = ?` with the snapshot
values) and skip the write when zero rows matched; or re-read the row
immediately before writing and recompute against fresh values. Add a test:
seed a row, start a verify pass, flip the row's status from another
connection mid-pass, assert the flip survives.

## High

### H1 — SSRF guard has a DNS-rebinding TOCTOU

`netguard.py:61-89`: `check_target()` resolves the hostname, validates every
returned IP is global, then `client.stream("GET", current)` performs its
**own independent resolution**. Nothing pins the connection to the validated
IPs. An attacker-controlled authoritative DNS returning a public record for
the validation lookup and `127.0.0.1`/`169.254.169.254` for the connect
bypasses the guard (also on redirect hops). The docstring's "checked on the
resolved IP of every hop" promise is only half-true: the check runs, but the
connect doesn't use the checked IP.

**Fix sketch:** custom httpx transport/resolver that resolves once and
connects to the validated addresses (e.g. wrap `httpx.HTTPTransport` with a
`network_backend` that returns a socket already connected to a vetted IP), or
re-resolve inside a lock and connect by IP with a Host header. The
`is_global` coverage and 2 MB body cap were empirically verified sound — the
rebind gap is the only hole in the guard.

### H2 — Boolean env parsing fails OPEN on typos

`config.py:40,42`:

```python
MUTATION_AUTH = os.getenv("MUTATION_AUTH", "1").strip().lower() in ("1", "true", "yes", "on")
```

`MUTATION_AUTH=enabled`, `=2`, `=tru` → evaluates **False** → every mutating
endpoint is silently unauthenticated, while `_check_auth_config()` stays
happy (it only catches auth-on + empty-token). Same for
`RATE_LIMIT_ENABLED`. The comment promises fail-closed; a typo defeats it.

**Fix sketch:** parse explicitly — only `0/false/no/off` disable; anything
else not in the truthy set raises at startup ("MUTATION_AUTH=enabled is not
a recognized value").

### H3 — Rate limiter collapses behind a reverse proxy (default config)

`main.py:~164` keys limits on `request.client.host`; the Dockerfile passes
`--proxy-headers` with `--forwarded-allow-ips="$FORWARDED_ALLOW_IPS"`
(default empty → uvicorn keeps the proxy IP). Behind any LB, **all clients
share one bucket**: one abuser (or aggressive frontend polling) 429s the
legitimate owner out of the admin gate. Setting `FORWARDED_ALLOW_IPS=*`
(the documented anti-pattern) lets any caller spoof `X-Forwarded-For` and
bypass all limits. Note `config.FORWARDED_ALLOW_IPS` is dead Python — only
the Dockerfile shell consumes the raw env var; the two can drift.

**Fix sketch:** document the per-platform recipe (Fly/Render/etc. expose the
real client IP differently); consider deriving the key from
`X-Forwarded-For` **only when** the direct peer is in a configured trust
list.

## Medium

- **M1 — QUEUES mutated under two different locks** (`seeder.py:74-78`
  appends under `_LOCK`, worker pops under `cond`; `_with_position` reads
  `.index()` under none). Correct today only via GIL atomicity; breaks under
  free-threaded CPython. Unify on one lock.
- **M2 — Job dicts shared between worker threads and request handlers**;
  `get_job` returns shallow copies whose nested `errors` lists the worker
  keeps appending to mid-serialization. Snapshot (json.dumps or copy) in the
  worker, or lock consistently.
- **M3 — Dedup race for normalization-equivalent URLs** (`db.py:29-30`):
  unique indexes on `lower(url)` are string identity, not normalized; two
  concurrent seeds of `https://zoom.com` vs `https://www.zoom.com/` both
  insert. Add a normalized-key column or serialize inserts through the
  kind-lock.
- **M4 — `bool(params.get("reuse_profile", True))` treats `"false"` as
  truthy** (`seeder.py:~342`); the admin seed endpoint accepts an unvalidated
  `params` dict. Coerce/validate all params.
- **M5 — 502/400 error detail leaks internal information**
  (`main.py:410-421`): httpx exceptions carry internal URLs; the SSRF guard
  raises `ValueError` → 400 with the guard's refusal message verbatim.
  Sanitize to generic messages; log the detail server-side.
- **M6 — Sort stability for paginated reads** (`main.py:~382`): no unique
  tiebreaker in `ORDER BY` → rows can swap between LIMIT/OFFSET pages. Add
  `id` as final tiebreaker.
- **M7 — O(N²) dedup scans + per-row connection churn in verify**: the
  `find_by_url` fallback re-normalizes the whole table on each miss;
  verify opens/commits ~2,600 connections per pass. Performance debt.
- **M8 — Job result blobs rewritten in full after every row**
  (`verify.py:316`); `errors`/bucket lists grow quadratically in write
  volume and the `jobs` table is never pruned (only `verify_log` has
  retention). Persist summaries at terminal state only + add jobs retention.

## Low / hygiene

- **L1 — Dead code:** `seeder.has_active_job` (never called); verify job
  skeleton carries `ok_urls` never appended; `UA_BROWSER` defined twice
  (`verify.py:19` / `website.py:14`); near-duplicate job skeletons in
  `seeder.py:44` vs `verify.py:90`.
- **L2 — Wrong docstring:** `main.py:~427` says verify runs are "serialized
  on the seed queue" — they run on their own queue in parallel.
- **L3 — Wayback fetched over plaintext HTTP** (`website.py:136`) — archive
  date can be MITM-poisoned; use HTTPS.
- **L4 — Human status endpoints don't bump `updated_at`**
  (`main.py:467-506`), so the audit column misses curation activity.
- **L5 — `/api/health` discloses `llm_model` + DB filename** — trivial, but
  free to redact.
- **L6 — `approve_suggested` created-window compares caller strings
  lexicographically** against SQLite's space-separated datetimes; an ISO-`T`
  input silently mis-compares. Validate the format.
- **L7 — HSTS header sent on plain-HTTP responses** (`main.py:145`) —
  meaningless without TLS termination; harmless.

## Verified correct (no action needed)

- Admin token comparison is timing-safe (`hmac.compare_digest`), failed
  attempts metered 10/min per IP.
- All SQL parameterized; LIKE wildcards escaped in the correct order.
- netguard body cap enforced mid-stream; redirect chains re-validated per
  hop including relative `Location` joins.
- `ipaddress.is_global` coverage confirmed on this runtime (blocks CGNAT,
  link-local metadata, IPv4-mapped IPv6, ULA, loopback).
- Restart recovery: queued/running jobs → `failed` with reason on boot;
  `--workers 1` constraint documented.
- WAL usage: per-call connections, `busy_timeout=5000`, per-row commits.
- Exclusive verify enqueue (`try_enqueue_exclusive`) is race-free.
