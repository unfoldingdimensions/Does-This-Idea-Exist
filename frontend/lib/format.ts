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
