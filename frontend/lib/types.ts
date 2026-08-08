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
  flagged: number;
  dead_flipped: string[];
}
