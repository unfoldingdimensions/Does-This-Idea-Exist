/** Display-formatting helpers — capitalization for tags, categories, languages. */

const SPECIAL: Record<string, string> = {
  ai: "AI",
  ui: "UI",
  api: "API",
  ghl: "GHL",
  seo: "SEO",
  saas: "SaaS",
  sqlite: "SQLite",
  devtools: "DevTools",
  typescript: "TypeScript",
  javascript: "JavaScript",
  nextjs: "Next.js",
  react: "React",
  vue: "Vue",
  go: "Go",
  rust: "Rust",
  python: "Python",
  swift: "Swift",
  kotlin: "Kotlin",
};

/** Capitalize the first letter; special-case common acronyms and tech names. */
export function titleCase(value: string | null | undefined): string {
  const s = (value ?? "").trim();
  if (!s) return "";
  if (SPECIAL[s.toLowerCase()]) return SPECIAL[s.toLowerCase()];
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Full date for detail views: "2026-08-09" / ISO → "Aug 9, 2026"; null/empty → "—". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Short date for cards: omits the year when it's the current year ("Aug 9"). */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const opts: Intl.DateTimeFormatOptions =
    d.getFullYear() === new Date().getFullYear()
      ? { month: "short", day: "numeric" }
      : { year: "numeric", month: "short", day: "numeric" };
  return d.toLocaleDateString("en-US", opts);
}
