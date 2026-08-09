import Fuse from "fuse.js";
import type { Startup } from "./types";

function createSearcher(startups: Startup[]): Fuse<Startup> {
  return new Fuse(startups, {
    keys: [
      { name: "name", weight: 3 },
      { name: "tagline", weight: 2 },
      { name: "description", weight: 1.5 },
      { name: "category", weight: 1 },
    ],
    // 0.3 (was 0.4): tight enough to exclude pure character-fuzz false positives
    // ("obsidian" → Avoca/Zoom), loose enough to keep fuzzy + deep-description hits.
    threshold: 0.3,
    ignoreLocation: true,
    includeScore: true,
  });
}

export interface Filters {
  q?: string;
  category?: string | null;
  year?: string | null;
  status?: string | null;
}

/**
 * Filter by query + facet: every whitespace-separated query term must fuzzy-match
 * somewhere (AND across terms — "markdown notes" hits Obsidian, not the whole grid);
 * category matches exactly; year matches the founded-year prefix; status maps
 * verified→verified===1, unverified→verified===0, dead→status==='dead'.
 */
export function filterStartups(startups: Startup[], filters: Filters): Startup[] {
  let out = startups;
  if (filters.category) {
    const cat = filters.category.trim().toLowerCase();
    out = out.filter((s) => (s.category ?? "").toLowerCase() === cat);
  }
  if (filters.year) out = out.filter((s) => (s.founded ?? "").startsWith(filters.year as string));
  if (filters.status) {
    out = out.filter((s) => {
      if (filters.status === "verified") return s.verified === 1;
      if (filters.status === "unverified") return s.verified === 0;
      if (filters.status === "dead") return s.status === "dead" || s.status === "pivoted";
      return true;
    });
  }
  const terms = (filters.q ?? "").trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return sortStartups(out);
  const searcher = createSearcher(out);
  // Per-term score maps; a term's match score is Fuse's normalized distance
  // (0 = exact, 1 = no match). Combined score = worst (max) term — AND semantics.
  const perTerm = terms.map((t) => new Map(searcher.search(t).map((r) => [r.item.id, r.score ?? 1])));
  const matchedIds = [...perTerm[0].keys()].filter((id) => perTerm.every((m) => m.has(id)));
  const byId = new Map(out.map((s) => [s.id, s]));
  const ranked = matchedIds
    .map((id) => ({ s: byId.get(id), score: Math.max(...perTerm.map((m) => m.get(id) ?? 1)) }))
    .filter((x): x is { s: Startup; score: number } => Boolean(x.s));
  // Relevance first (the exact-name match ranks #1, not the most-starred hit),
  // dead/pivoted entries sink to the bottom, stars break ties.
  ranked.sort(
    (a, b) => DEAD_ORDER(a.s) - DEAD_ORDER(b.s) || a.score - b.score || (b.s.stars ?? 0) - (a.s.stars ?? 0),
  );
  return ranked.map((x) => x.s);
}

export type SortKey = "top" | "newest" | "verified" | "name" | "founded";

const DEAD_ORDER = (s: Startup) => (s.status === "dead" || s.status === "pivoted" ? 1 : 0);
const ts = (iso: string | null | undefined): number => (iso ? new Date(iso).getTime() : 0);

/**
 * Sort by key; every key sinks dead/pivoted entries to the bottom first (the
 * directory never promotes dead entries), then applies the requested ordering.
 */
export function sortStartups(startups: Startup[], key: SortKey = "top"): Startup[] {
  const arr = [...startups];
  arr.sort((a, b) => DEAD_ORDER(a) - DEAD_ORDER(b));
  const starsTiebreak = (a: Startup, b: Startup) => (b.stars ?? 0) - (a.stars ?? 0);
  switch (key) {
    case "newest":
      return arr.sort((a, b) => ts(b.created_at) - ts(a.created_at) || starsTiebreak(a, b));
    case "verified":
      return arr.sort((a, b) => ts(b.verified_at) - ts(a.verified_at) || starsTiebreak(a, b));
    case "name":
      return arr.sort((a, b) => a.name.localeCompare(b.name));
    case "founded":
      return arr.sort((a, b) => ts(b.founded) - ts(a.founded) || starsTiebreak(a, b));
    default: // top
      return arr.sort((a, b) => starsTiebreak(a, b) || a.name.localeCompare(b.name));
  }
}

export function foundedYear(founded: string | null): string | null {
  if (!founded) return null;
  const m = founded.match(/\d{4}/);
  return m ? m[0] : null;
}
