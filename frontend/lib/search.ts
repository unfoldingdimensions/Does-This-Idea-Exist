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
    threshold: 0.4,
    ignoreLocation: true,
  });
}

/**
 * Filter by query: every whitespace-separated term must fuzzy-match somewhere in the
 * startup (AND across terms), so "markdown notes" hits Obsidian but not the whole grid.
 */
export function filterStartups(startups: Startup[], query: string): Startup[] {
  const terms = query.trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return sortStartups(startups);
  const searcher = createSearcher(startups);
  const perTerm = terms.map((t) => new Set(searcher.search(t).map((r) => r.item.id)));
  const matchedIds = [...perTerm[0]].filter((id) => perTerm.every((s) => s.has(id)));
  const byId = new Map(startups.map((s) => [s.id, s]));
  return sortStartups(
    matchedIds.map((id) => byId.get(id)).filter((s): s is Startup => Boolean(s)),
  );
}

/** Order: active first (by name), dead/pivoted last — matches backend ordering. */
export function sortStartups(startups: Startup[]): Startup[] {
  return [...startups].sort((a, b) => {
    const dead = (s: Startup) => (s.status === "dead" || s.status === "pivoted" ? 1 : 0);
    if (dead(a) !== dead(b)) return dead(a) - dead(b);
    return a.name.localeCompare(b.name);
  });
}

export function foundedYear(founded: string | null): string | null {
  if (!founded) return null;
  const m = founded.match(/\d{4}/);
  return m ? m[0] : null;
}
