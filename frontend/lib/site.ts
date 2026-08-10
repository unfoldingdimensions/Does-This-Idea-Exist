// Same additive env pattern as NEXT_PUBLIC_API_BASE: hosts set the real
// origin at build time; the local default reflects the dev truth.
export const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3023";
