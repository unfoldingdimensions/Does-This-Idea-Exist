import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

// The sitemap lists the home page AND every product page: `/products/<slug>`
// is the stable per-product address (F-17) that "Share Entity" copies, so it
// is exactly what a search engine should index. Slugs are fetched live from
// the backend at sitemap build/request time — a backend that is down yields
// the home page alone instead of a broken build.
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
  try {
    const res = await fetch(`${apiBase}/api/startups?limit=5000`, {
      cache: "no-store",
    });
    if (!res.ok) return entries;
    const rows: Array<{ name: string }> = await res.json();
    for (const row of rows) {
      if (!row?.name) continue;
      // Mirror of the backend's compare.slugify (lowercase, non-alphanumeric
      // runs -> '-') — the client-side copy in teardown-dossier.tsx is the
      // reference; keep the two in step.
      const slug = row.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
      if (!slug) continue;
      entries.push({
        url: `${siteUrl}/products/${slug}`,
        lastModified: new Date(),
        changeFrequency: "weekly",
        priority: 0.6,
      });
    }
  } catch {
    // backend unreachable at build time: ship the home page alone
  }
  return entries;
}
