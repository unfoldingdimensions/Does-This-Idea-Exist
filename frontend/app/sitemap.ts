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

/** Mirror of the backend's compare.slugify (lowercase, non-alphanumeric runs
 * -> '-') — the client-side copy in teardown-dossier.tsx is the reference;
 * keep the two in step. */
function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

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
  try {
    // Walk pages until a short page (or the safety cap) ends the loop.
    for (let page = 0; page < 100; page++) {
      const res = await fetch(
        `${apiBase}/api/startups/page?limit=${PAGE}&offset=${offset}`,
        { cache: "no-store" },
      );
      if (!res.ok) break;
      const body: { total?: number; rows?: Array<{ name: string }> } =
        await res.json();
      const rows = body.rows ?? [];
      for (const row of rows) {
        if (!row?.name) continue;
        const slug = slugify(row.name);
        if (!slug) continue;
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
