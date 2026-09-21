import type {
  CategoryCount,
  CompareResult,
  FounderAppDetail,
  FounderAppDraft,
  FounderPublishResult,
  LlmGateway,
  LlmGatewayPatch,
  LlmGatewayTestResult,
  LlmGatewaysView,
  SearchResult,
  SeedJob,
  Startup,
  StartupRecord,
  Stats,
  SuggestedStartup,
  VerifyJob,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8020";

/** A hung backend (TCP accept, no response) used to leave the UI on the
 * skeleton forever — the offline banner only surfaced on REJECTION. Every
 * request now carries a hard deadline so a stall degrades into the same
 * unreachable state (with its Retry) instead of a frozen page. Reads get a
 * snappy 10s; the seed POSTs wait on fetch+LLM so they get 90s. */
const READ_TIMEOUT_MS = 10_000;
const WRITE_TIMEOUT_MS = 90_000;

function withTimeout(init: RequestInit | undefined, ms: number): RequestInit {
  const signal = AbortSignal.timeout(ms);
  if (!init?.signal) return { ...init, signal };
  // Respect an explicit caller signal: abort when either fires.
  const callerSignal = init.signal;
  const timeoutSignal = signal;
  return {
    ...init,
    signal: AbortSignal.any([callerSignal, timeoutSignal]),
  };
}

/** Best-effort error detail from a non-OK response (backend sends {detail}). */
async function errorDetail(res: Response): Promise<string> {
  let detail = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    if (body?.detail) detail = String(body.detail);
  } catch {
    /* non-JSON error body */
  }
  return detail;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, withTimeout(init, READ_TIMEOUT_MS));
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json() as Promise<T>;
}

/** The archive arrives in one fetch — client-side search/facets run over it.
 * (The backend still accepts ?q=/?category=, but nothing on this side does
 * server-side filtering.) */
export function fetchStartups(): Promise<Startup[]> {
  return json<Startup[]>(`${API_BASE}/api/startups`, { cache: "no-store" });
}

export function fetchCategories(): Promise<CategoryCount[]> {
  return json<CategoryCount[]>(`${API_BASE}/api/categories`, { cache: "no-store" });
}

export function fetchStats(): Promise<Stats> {
  return json<Stats>(`${API_BASE}/api/stats`, { cache: "no-store" });
}

export function seedByGithub(githubUrl: string): Promise<Startup> {
  return adminJson<Startup>(`${API_BASE}/api/seed/github`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

export function seedByWebsite(websiteUrl: string, name?: string): Promise<Startup> {
  return adminJson<Startup>(`${API_BASE}/api/seed/website`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ website_url: websiteUrl, name: name || null }),
  });
}

export function runVerification(): Promise<{ job_id: string }> {
  return adminJson<{ job_id: string }>(`${API_BASE}/api/verify/run`, { method: "POST" });
}

// Job payloads carry error strings + seeded URLs, so these live behind the
// admin gate on the backend.
export function verificationStatus(jobId: string): Promise<VerifyJob> {
  return adminJson<VerifyJob>(`${API_BASE}/api/admin/verify/status/${jobId}`, { cache: "no-store" });
}

export function currentVerification(): Promise<VerifyJob | null> {
  return adminJson<VerifyJob | null>(`${API_BASE}/api/admin/verify/current`, { cache: "no-store" });
}

export function fetchSuggested(): Promise<SuggestedStartup[]> {
  return adminJson<SuggestedStartup[]>(`${API_BASE}/api/admin/verify/suggested`, {
    cache: "no-store",
  });
}

export function approveSuggested(
  ids?: number[],
  approveAll?: boolean,
  createdAfter?: string,
  createdBefore?: string,
): Promise<{ approved: number }> {
  let body: Record<string, unknown>;
  if (createdAfter || createdBefore) {
    body = { created_after: createdAfter, created_before: createdBefore };
  } else {
    body = approveAll ? { approve_all: true } : { ids };
  }
  return adminJson<{ approved: number }>(`${API_BASE}/api/admin/verify/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Mutations require the owner token (MUTATION_AUTH defaults on). adminJson —
// not json — so a 403 surfaces as AdminUnauthorized and the caller can prompt
// for a fresh token instead of showing an opaque error toast.
export function markVerified(id: number): Promise<Startup> {
  return adminJson<Startup>(`${API_BASE}/api/startups/${id}/verify`, { method: "POST" });
}

/** Decide a FOUNDER publish request (kind "founder_submission" in the
 * suggested queue). Never call approveSuggested for these rows: the id is a
 * submissions-table id, and the archive approve would silently update a
 * completely different startups row (or nothing). */
export function approveSubmission(submissionId: number): Promise<Record<string, unknown>> {
  return adminJson<Record<string, unknown>>(
    `${API_BASE}/api/admin/founder/submissions/${submissionId}/approve`,
    { method: "POST" },
  );
}

export function rejectSubmission(
  submissionId: number,
  note: string,
): Promise<Record<string, unknown>> {
  return adminJson<Record<string, unknown>>(
    `${API_BASE}/api/admin/founder/submissions/${submissionId}/reject`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    },
  );
}

export function markUnverified(id: number): Promise<Startup> {
  return adminJson<Startup>(`${API_BASE}/api/startups/${id}/unverify`, { method: "POST" });
}

export function markDead(id: number): Promise<Startup> {
  return adminJson<Startup>(`${API_BASE}/api/startups/${id}/dead`, { method: "POST" });
}

// --- Admin (owner-only seeder) ---

const ADMIN_TOKEN_KEY = "ideasexist.admin.token";
const tokenListeners = new Set<() => void>();

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null; // SSR/prerender guard
  return sessionStorage.getItem(ADMIN_TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
  tokenListeners.forEach((l) => l());
}

export function clearAdminToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  tokenListeners.forEach((l) => l());
}

/**
 * Subscribe to lock/unlock. Write controls live all over the tree (header
 * split-button, empty state, every card's status pill), so they read this
 * instead of having a token prop threaded down through the grid.
 */
export function subscribeAdminToken(listener: () => void): () => void {
  tokenListeners.add(listener);
  return () => {
    tokenListeners.delete(listener);
  };
}

function adminHeaders(): Record<string, string> {
  const token = getAdminToken();
  return token ? { "X-Admin-Token": token } : {};
}

export class AdminUnauthorized extends Error {
  constructor() {
    super("Admin token invalid or expired");
    this.name = "AdminUnauthorized";
  }
}

async function adminJson<T>(url: string, init?: RequestInit): Promise<T> {
  // Mutating calls (seed/verify-run/approve) wait on fetch+LLM server-side,
  // so they get the longer deadline; reads stay snappy. no-store on all of
  // them — the 2s job poll especially must never be heuristic-cached.
  const ms = init?.method === "POST" ? WRITE_TIMEOUT_MS : READ_TIMEOUT_MS;
  const res = await fetch(url, {
    ...withTimeout(init, ms),
    headers: { ...adminHeaders(), ...init?.headers },
    cache: "no-store",
  });
  if (res.status === 403) {
    throw new AdminUnauthorized();
  }
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json() as Promise<T>;
}

export function adminCheck(token: string): Promise<{ ok: boolean }> {
  return fetch(`${API_BASE}/api/admin/check`, {
    headers: { "X-Admin-Token": token },
    cache: "no-store",
    signal: AbortSignal.timeout(READ_TIMEOUT_MS),
  }).then(async (res) => {
    if (res.status === 403) throw new AdminUnauthorized();
    if (!res.ok) throw new Error(await errorDetail(res));
    return res.json();
  });
}

export function startSeed(source: string, params: Record<string, unknown>): Promise<{ job_id: string }> {
  return adminJson<{ job_id: string }>(`${API_BASE}/api/admin/seed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, params }),
  });
}

export function fetchSeedJobs(): Promise<SeedJob[]> {
  return adminJson<SeedJob[]>(`${API_BASE}/api/admin/seed/jobs`);
}

// --- Phase 6: the verified surface the product UI consumes -------------------
// Everything below is wired to the Phase 5-verified backend. No mocks, no
// hardcoded rows: the non-happy answers are normal answers here, and each one
// gets its own shape so the UI can render it honestly instead of an empty box.

/**
 * Best-effort detail from an error body we already read as text.
 * FastAPI puts a STRING in `detail` for most refusals but a DICT for the ones
 * the product models as states (compare's 409 `{state, message}`), so a plain
 * `String(detail)` would print `[object Object]` at the user.
 */
function detailMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message) return message;
    return JSON.stringify(detail);
  }
  return `HTTP ${status}`;
}

async function readBody(res: Response): Promise<unknown> {
  try {
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  } catch {
    return null; // non-JSON error body
  }
}

/**
 * `POST /api/compare` refused an UNCONFIRMED draft (409 `{state: "not_confirmed"}`).
 * Its own class because the honest UI response is not an error toast — it is to
 * say so and walk the founder to the confirm step, never to render a table.
 */
export class CompareNotConfirmed extends Error {
  readonly state = "not_confirmed" as const;
  constructor(message: string) {
    super(message);
    this.name = "CompareNotConfirmed";
  }
}

/**
 * The gap table (F-15). Returns the table, OR the explicit capture-pending
 * state (`queued` / `in_progress`) the JIT capture answers with while a
 * competitor's teardown is being read — the caller must offer a retry and must
 * never render a partial table as if it were the answer.
 *
 * The two sides live in two different databases, so the request namespaces them
 * (`{you, competitors}`) rather than passing one flat id list.
 */
export async function compareStartups(
  you: string,
  competitors: string[],
): Promise<CompareResult> {
  const res = await fetch(
    `${API_BASE}/api/compare`,
    withTimeout(
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...founderHeaders(you) },
        body: JSON.stringify({ you, competitors }),
      },
      WRITE_TIMEOUT_MS,
    ),
  );
  const body = await readBody(res);
  if (res.status === 409) {
    throw new CompareNotConfirmed(
      detailMessage(body, res.status) ||
        "the draft must be confirmed before the gap table can run",
    );
  }
  if (!res.ok) throw new Error(detailMessage(body, res.status));
  return body as CompareResult;
}

/**
 * `/api/startups/{slug}` has no such product (404). Its own class because the
 * honest response is a themed "nothing in the archive matches" page — which is
 * a different state from the archive being unreachable, and a different state
 * again from the read failing.
 */
export class RecordNotFound extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RecordNotFound";
  }
}

/** `GET /api/startups/{slug}` — the stable per-product record (F-17). */
export async function fetchStartupRecord(slug: string): Promise<StartupRecord> {
  const res = await fetch(
    `${API_BASE}/api/startups/${encodeURIComponent(slug)}`,
    withTimeout({ cache: "no-store" }, READ_TIMEOUT_MS),
  );
  const body = await readBody(res);
  if (res.status === 404) throw new RecordNotFound(detailMessage(body, res.status));
  if (!res.ok) throw new Error(detailMessage(body, res.status));
  return body as StartupRecord;
}

/**
 * `GET /api/search` — classified results carrying the server's frozen per-result
 * `reason` (F-18). An empty/blank query returns 200 with `[]` by contract, so
 * "no query" and "no matches" are the same harmless state.
 */
export function searchStartups(q: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q });
  return json<SearchResult[]>(`${API_BASE}/api/search?${params}`, { cache: "no-store" });
}

/** The three export formats `GET /api/export/{format}` serves. */
export type ExportFormat = "markdown" | "json" | "csv";

export interface ExportPayload {
  text: string;
  mediaType: string;
  filename: string;
}

/**
 * `GET /api/export/{format}` — the same inputs as `/api/compare`, recomputed
 * and returned as bytes (F-16). Stateless on purpose: there is no stored "last
 * comparison" to read back, so the same inputs always yield the same bytes.
 * It never triggers a capture, so it can be called the moment the table renders.
 */
export async function exportGapTable(
  format: ExportFormat,
  you: string,
  competitors: string[],
): Promise<ExportPayload> {
  const params = new URLSearchParams({ you });
  competitors.forEach((c) => params.append("competitors", c));
  const res = await fetch(
    `${API_BASE}/api/export/${format}?${params}`,
    withTimeout({ headers: { ...founderHeaders(you) } }, WRITE_TIMEOUT_MS),
  );
  if (res.status === 409) {
    throw new CompareNotConfirmed(
      detailMessage(await readBody(res), res.status) ||
        "the draft must be confirmed before it can be exported",
    );
  }
  if (!res.ok) throw new Error(detailMessage(await readBody(res), res.status));
  return {
    text: await res.text(),
    mediaType: res.headers.get("content-type") ?? "",
    filename: `gap-table.${format}`,
  };
}

// --- the founder's own store (F-10..F-13, F-20) ------------------------------
// Deliberately NOT behind the admin token: none of these can write the archive,
// so the token that guards archive mutations would only stand between a founder
// and their own local draft. Every call is rate-limited server-side.
//
// Each draft carries its own per-draft secret instead: the creation response
// includes a one-time `founder_token`, stored here (sessionStorage, like the
// admin token — a tab-local secret, never in a URL) and sent back as
// X-Founder-Token. Sequential draft ids are not enumerable without it.

const FOUNDER_TOKENS_KEY = "ideasexist.founder.tokens";

function readFounderTokens(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(sessionStorage.getItem(FOUNDER_TOKENS_KEY) ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
}

/** Remember a draft's token under its id (and name slug, for slug-addressed calls). */
export function storeFounderToken(id: number, token: string, slug?: string): void {
  if (typeof window === "undefined" || !token) return;
  const tokens = readFounderTokens();
  tokens[String(id)] = token;
  if (slug) tokens[slug.toLowerCase()] = token;
  try {
    sessionStorage.setItem(FOUNDER_TOKENS_KEY, JSON.stringify(tokens));
  } catch {
    /* storage full or unavailable — the next call just 403s honestly */
  }
}

function founderTokenFor(you: string | number): string | null {
  const tokens = readFounderTokens();
  const direct = tokens[String(you)];
  if (direct) return direct;
  if (typeof you === "string") {
    const lowered = you.toLowerCase();
    const hit = tokens[lowered];
    if (hit) return hit;
  }
  return null;
}

function founderHeaders(you?: string | number): Record<string, string> {
  if (you === undefined) return {};
  const token = founderTokenFor(you);
  return token ? { "X-Founder-Token": token } : {};
}

function founderJson<T>(path: string, init?: RequestInit, you?: string | number): Promise<T> {
  const ms = init?.method === "POST" ? WRITE_TIMEOUT_MS : READ_TIMEOUT_MS;
  return fetch(`${API_BASE}${path}`, {
    ...withTimeout(init, ms),
    // Never a `publish` field on create: it is a 422 on purpose. Create →
    // confirm → publish are three calls.
    headers: { "Content-Type": "application/json", ...founderHeaders(you), ...init?.headers },
    cache: "no-store",
  }).then(async (res) => {
    if (!res.ok) throw new Error(detailMessage(await readBody(res), res.status));
    return (await res.json()) as T;
  });
}

/**
 * Draft the founder's own app. Exactly one path per call: `agent_json` (paste),
 * `url`, or the form fields. Nothing is auto-confirmed and nothing auto-diffs.
 *
 * The response carries the draft's one-time `founder_token` — stored here so
 * every later read/confirm/publish/compare of this draft can prove ownership.
 */
export function createFounderApp(
  body: Record<string, unknown>,
): Promise<FounderAppDraft> {
  return founderJson<FounderAppDraft>("/api/founder-app", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((draft) => {
    if (draft.founder_token) {
      storeFounderToken(draft.founder_app_id, draft.founder_token, draft.profile?.name);
    }
    return draft;
  });
}

/** The draft plus the derived `archive_status` and every decision on it. */
export function getFounderApp(id: number): Promise<FounderAppDetail> {
  return founderJson<FounderAppDetail>(`/api/founder-app/${id}`, undefined, id);
}

/** The confirm-before-diff gate (F-13) — the gap table's precondition. */
export function confirmFounderApp(id: number): Promise<FounderAppDraft> {
  return founderJson<FounderAppDraft>(`/api/founder-app/${id}/confirm`, { method: "POST" }, id);
}

/**
 * The consent gate on its own. Eligibility has already been checked first.
 *
 * Returns the SUBMISSION acknowledgement, not the draft — the route answers
 * `{submitted, submission_id, archive_status, message}`. Call `getFounderApp`
 * afterwards for the authoritative record: trusting this payload as a draft would
 * put a `profile` on screen that the response never carried.
 */
export function publishFounderApp(id: number): Promise<FounderPublishResult> {
  return founderJson<FounderPublishResult>(`/api/founder-app/${id}/publish`, { method: "POST" }, id);
}

// --- LLM gateways (docs/llm-gateways.md §4) ---------------------------------
// Through adminJson, which attaches the owner token and turns a 403 into
// AdminUnauthorized — that is what makes the panel lock itself when the session
// goes stale. No response ever carries a key; the field is write-only.

export function fetchLlmGateways(): Promise<LlmGatewaysView> {
  return adminJson<LlmGatewaysView>(`${API_BASE}/api/admin/settings/gateways`, {
    cache: "no-store",
  });
}

/** Patch one gateway. Omitted field = left alone; `""` = clear the override. */
export function updateLlmGateway(
  id: string,
  patch: LlmGatewayPatch,
): Promise<LlmGateway> {
  return adminJson<LlmGateway>(`${API_BASE}/api/admin/settings/gateways/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

/** Make a `ready` gateway the one every seed and capture uses. 400 when not. */
export function setActiveLlmGateway(id: string): Promise<LlmGatewaysView> {
  return adminJson<LlmGatewaysView>(`${API_BASE}/api/admin/settings/gateways/active`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gateway_id: id }),
  });
}

/** Back to the gateway `backend/.env` describes. */
export function resetActiveLlmGateway(): Promise<LlmGatewaysView> {
  return adminJson<LlmGatewaysView>(`${API_BASE}/api/admin/settings/gateways/active/reset`, {
    method: "POST",
  });
}

/**
 * One real, tiny completion against THAT gateway — active or not, so a key can
 * be checked before it is switched in. Always 200 unless the id is unknown:
 * a bad key and a blocked target are results, not faults.
 */
export function testLlmGateway(id: string): Promise<LlmGatewayTestResult> {
  return adminJson<LlmGatewayTestResult>(
    `${API_BASE}/api/admin/settings/gateways/${id}/test`,
    { method: "POST" },
  );
}
