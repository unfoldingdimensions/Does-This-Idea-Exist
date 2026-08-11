import type { CategoryCount, SeedJob, Startup, Stats, SuggestedStartup, VerifyJob } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8020";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function fetchStartups(q?: string, category?: string): Promise<Startup[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  const qs = params.toString();
  return json<Startup[]>(`${API_BASE}/api/startups${qs ? `?${qs}` : ""}`, { cache: "no-store" });
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
  const res = await fetch(url, { ...init, headers: { ...adminHeaders(), ...init?.headers } });
  if (res.status === 403) {
    throw new AdminUnauthorized();
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function adminCheck(token: string): Promise<{ ok: boolean }> {
  return fetch(`${API_BASE}/api/admin/check`, {
    headers: { "X-Admin-Token": token },
  }).then((res) => {
    if (res.status === 403) throw new AdminUnauthorized();
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
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

export function seedStatus(jobId: string): Promise<SeedJob> {
  return adminJson<SeedJob>(`${API_BASE}/api/admin/seed/status/${jobId}`);
}

export function fetchSeedJobs(): Promise<SeedJob[]> {
  return adminJson<SeedJob[]>(`${API_BASE}/api/admin/seed/jobs`);
}
