import type { CategoryCount, Startup, Stats, VerifyResult } from "./types";

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
  return json<Startup>(`${API_BASE}/api/seed/github`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

export function seedByWebsite(websiteUrl: string, name?: string): Promise<Startup> {
  return json<Startup>(`${API_BASE}/api/seed/website`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ website_url: websiteUrl, name: name || null }),
  });
}

export function runVerification(): Promise<VerifyResult> {
  return json<VerifyResult>(`${API_BASE}/api/verify/run`, { method: "POST" });
}
