export interface Startup {
  id: number;
  name: string;
  tagline: string | null;
  description: string | null;
  category: string | null;
  website_url: string | null;
  github_url: string | null;
  founded: string | null;
  stars: number | null;
  language: string | null;
  status: "active" | "pivoted" | "dead";
  verified: number;
  verified_at: string | null;
  last_checked: string | null;
  check_failures: number;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface Stats {
  total: number;
  verified: number;
  dead: number;
  last_checked: string | null;
}

export interface VerifyResult {
  checked: number;
  ok: number;
  skipped: number;
  flagged: number;
  dead_flipped: string[];
  breakdown: { verified: number; unverified: number; dead: number };
  already_verified: { id: number; name: string; url: string }[];
  suggested: { id: number; name: string; url: string }[];
  failed_list: { id: number; name: string; url: string; reason: string }[];
}

export interface SuggestedStartup {
  id: number;
  name: string;
  website_url: string | null;
  github_url: string | null;
  category: string;
  last_checked: string | null;
  created_at: string;
}

export interface VerifyJob {
  id: string;
  kind: string;
  source: string;
  status: "queued" | "running" | "done" | "failed";
  queue_position: number | null;
  total: number;
  done: number;
  ok: number;
  skipped: number;
  failed: number;
  errors: string[];
  current: string;
  breakdown: { verified: number; unverified: number; dead: number };
  result: VerifyResult | null;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
}

export interface SeedJob {
  id: string;
  kind: "seed" | "verify";
  source: string;
  status: "queued" | "running" | "done" | "failed";
  queue_position: number | null;
  total: number;
  done: number;
  ok: number;
  skipped: number;
  failed: number;
  errors: string[];
  ok_urls: string[];
  skipped_urls: string[];
  current: string;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  /** Verify jobs carry their full result (buckets etc.) once terminal. */
  result: VerifyResult | null;
}
