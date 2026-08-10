import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

// Single-route app: the archive lives on "/" with query params (search,
// filters) that all canonicalize to the homepage. Nothing else is indexable.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${siteUrl}/`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
