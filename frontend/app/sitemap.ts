import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

// The sitemap lists the home page AND every product page: `/products/<slug>`
// is the stable per-product address (F-17) that "Share Entity" copies, so it
// is exactly what a search engine should index. Slugs are fetched live from
// the backend at sitemap build/request time — a backend that is down yields
// the home page alone instead of a broken build.
//
// Phase P (scale-plan §7.1): the walk uses the paged envelope endpoint so the
// sitemap covers the WHOLE archive instead of silently stopping at the old
// 5,000-row read ceiling. Any failed page keeps what was collected so far —
// a partial sitemap beats a broken build.
//
// Phase P task 7b — two classes of URL are deliberately NOT emitted:
//
//   1. TOMBSTONES. A `dead` or `pivoted` row is a product the archive has
//      retired; advertising it to crawlers points them at a page whose entire
//      meaning is that the idea died. (Measured 2026-09-24: 0 such rows in the
//      live archive — all 1,258 are `active` — so this is a guard for the day
//      one is filed, not a cleanup.)
//   2. DUPLICATE SLUGS. Slugs come from the name, and the name is not unique:
//      6 name-pairs collide today ("Cal.com", "Bun", "Fathom", "Motion",
//      "Stability AI", "Bird") — 1,252 distinct URLs out of 1,258 rows.
//      `/api/startups/{slug}` resolves a collision deterministically
//      (verified-first, then lowest id — `compare._slug_candidates`), so ONE
//      page exists per slug and a repeated <loc> would be a duplicate, not a
//      second page. The colliding ROWS are a §7.6 identity question (some
//      pairs are genuinely different companies — Fathom the notetaker vs
//      Fathom the medical coder, Motion the animation library vs Motion the
//      work app) — do not settle it here.

/** Mirror of the backend's compare.slugify (lowercase, non-alphanumeric runs
 * -> '-') — the client-side copy in teardown-dossier.tsx is the reference;
 * keep the two in step. */
function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Rows a sitemap must never advertise: a retired product is not a result. */
const TOMBSTONE_STATUSES = new Set(["dead", "pivoted"]);

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [
    {
      url: `${siteUrl}/`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];

  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8020";
  const PAGE = 500;
  let offset = 0;
  // One URL per slug — the page resolves to a single row even when two rows
  // share a name.
  const seen = new Set<string>();
  try {
    // Walk pages until a short page (or the safety cap) ends the loop.
    for (let page = 0; page < 100; page++) {
      const res = await fetch(
        `${apiBase}/api/startups/page?limit=${PAGE}&offset=${offset}`,
        { cache: "no-store" },
      );
      if (!res.ok) break;
      const body: {
        total?: number;
        rows?: Array<{ name: string; status?: string }>;
      } = await res.json();
      const rows = body.rows ?? [];
      for (const row of rows) {
        if (!row?.name) continue;
        if (row.status && TOMBSTONE_STATUSES.has(row.status)) continue;
        const slug = slugify(row.name);
        if (!slug || seen.has(slug)) continue;
        seen.add(slug);
        entries.push({
          url: `${siteUrl}/products/${slug}`,
          lastModified: new Date(),
          changeFrequency: "weekly",
          priority: 0.6,
        });
      }
      offset += rows.length;
      const total = body.total ?? 0;
      if (rows.length < PAGE || offset >= total) break;
    }
  } catch {
    // backend unreachable at build time: ship whatever was collected (at
    // least the home page)
  }
  return entries;
}
