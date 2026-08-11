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

// One Fuse index per source array, cached by identity. The page's `startups`
// state array is stable between renders, so keystrokes reuse the index —
// rebuilding it every keystroke measured 120-180ms of input jank over 1,292
// rows (the "debounced" comment in page.tsx was a lie until the debounce landed).
const searcherCache = new WeakMap<Startup[], Fuse<Startup>>();
function searcherFor(startups: Startup[]): Fuse<Startup> {
  let searcher = searcherCache.get(startups);
  if (!searcher) {
    searcher = createSearcher(startups);
    searcherCache.set(startups, searcher);
  }
  return searcher;
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
  const facetOk = (s: Startup): boolean => {
    if (filters.category && (s.category ?? "").toLowerCase() !== filters.category) return false;
    if (filters.year && !(s.founded ?? "").startsWith(filters.year as string)) return false;
    if (filters.status === "verified") return s.verified === 1;
    if (filters.status === "unverified") return s.verified === 0;
    if (filters.status === "dead") return s.status === "dead" || s.status === "pivoted";
    return true;
  };
  const terms = (filters.q ?? "").trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return sortStartups(startups.filter(facetOk));
  // Facets apply to the matches (scores are per-document, so matching against
  // the full cached index then facet-filtering equals matching the filtered
  // pool — but the index is rebuilt once per data load instead of per keystroke).
  const searcher = searcherFor(startups);
  // Per-term score maps; a term's match score is Fuse's normalized distance
  // (0 = exact, 1 = no match). Combined score = worst (max) term — AND semantics.
  const perTerm = terms.map((t) => new Map(searcher.search(t).map((r) => [r.item.id, r.score ?? 1])));
  const matchedIds = [...perTerm[0].keys()].filter((id) => perTerm.every((m) => m.has(id)));
  const byId = new Map(startups.map((s) => [s.id, s]));
  const ranked = matchedIds
    .map((id) => ({ s: byId.get(id), score: Math.max(...perTerm.map((m) => m.get(id) ?? 1)) }))
    .filter((x): x is { s: Startup; score: number } => {
      if (!x.s || !facetOk(x.s)) return false;
      return true;
    })
    // Relevance first (the exact-name match ranks #1, not the most-starred hit),
    // dead/pivoted entries sink to the bottom, stars break ties.
    .sort(
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
 *
 * DEAD_ORDER has to lead each comparator rather than run as a separate pre-sort
 * pass: a second full sort() reorders the array wholesale, and stability only
 * preserves order between elements the NEW comparator calls equal — so a
 * pre-sort would be discarded for every key that isn't already dead-aware.
 */
export function sortStartups(startups: Startup[], key: SortKey = "top"): Startup[] {
  const arr = [...startups];
  const dead = (a: Startup, b: Startup) => DEAD_ORDER(a) - DEAD_ORDER(b);
  const starsTiebreak = (a: Startup, b: Startup) => (b.stars ?? 0) - (a.stars ?? 0);
  switch (key) {
    case "newest":
      return arr.sort((a, b) => dead(a, b) || ts(b.created_at) - ts(a.created_at) || starsTiebreak(a, b));
    case "verified":
      return arr.sort((a, b) => dead(a, b) || ts(b.verified_at) - ts(a.verified_at) || starsTiebreak(a, b));
    case "name":
      return arr.sort((a, b) => dead(a, b) || a.name.localeCompare(b.name));
    case "founded":
      return arr.sort((a, b) => dead(a, b) || ts(b.founded) - ts(a.founded) || starsTiebreak(a, b));
    default: // top — trust-weighted: verified first, then stars, then name
      return arr.sort(
        (a, b) =>
          dead(a, b) || (b.verified - a.verified) || starsTiebreak(a, b) || a.name.localeCompare(b.name),
      );
  }
}

export function foundedYear(founded: string | null): string | null {
  if (!founded) return null;
  const m = founded.match(/\d{4}/);
  return m ? m[0] : null;
}
