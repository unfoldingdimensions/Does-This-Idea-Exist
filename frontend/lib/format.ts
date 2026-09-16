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

/**
 * Parse a backend timestamp into a Date, or null when unparseable.
 *
 * SQLite `datetime('now')` writes UTC as "YYYY-MM-DD HH:MM:SS" — a space-
 * separated form `new Date()` reads as LOCAL time, shifting every derived
 * label and sort by the viewer's UTC offset (wrong day near midnight). Only
 * that exact DB-datetime shape gets normalized to ISO UTC; date-only
 * ("2026-08-09") and year-only ("2020") strings already parse per spec and
 * must pass through untouched.
 */
export function parseDbDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const s = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(iso) ? `${iso.replace(" ", "T")}Z` : iso;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Full date for detail views: "2026-08-09" / ISO → "Aug 9, 2026"; null/empty → "—". */
export function formatDate(iso: string | null | undefined): string {
  const d = parseDbDate(iso);
  if (!d) return "—";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Short date for cards: omits the year when it's the current year ("Aug 9"). */
export function shortDate(iso: string | null | undefined): string {
  const d = parseDbDate(iso);
  if (!d) return "—";
  const opts: Intl.DateTimeFormatOptions =
    d.getFullYear() === new Date().getFullYear()
      ? { month: "short", day: "numeric" }
      : { year: "numeric", month: "short", day: "numeric" };
  return d.toLocaleDateString("en-US", opts);
}

/** Deterministic hue (0–360) from a name — the Identicon pattern (GitHub, 2013):
 * faceless entries still get a stable color identity. Same name → same hue, always. */
function hueFromName(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0;
  }
  return h % 360;
}

/**
 * WHERE a date came from (F-04). `founded` may hold an RDAP domain-registration
 * date or a Wayback first-capture date rather than a founding year (Notion is
 * filed 2000-11-01 and was founded in 2013), so the display is only allowed to
 * call it a founding year when a human actually confirmed it.
 */
export type DateSource = "llm" | "wayback" | "rdap" | "human" | "unknown";

/** The column arrives as TEXT, so callers hand over a plain string; anything
 * outside the vocabulary falls through to the "unrecorded" branch below. */
type LooseDateSource = DateSource | string | null | undefined;

/**
 * The honest label for a `founded` value — the frontend half of F-04.
 *
 * Returns the term to print (`Founded`, `Domain registered`, `First archived`),
 * the raw value (null when there is none — never a fabricated year), and a note
 * explaining the approximation when the source is not a human confirmation.
 */
export function foundedLabel(
  founded: string | null | undefined,
  dateSource: LooseDateSource,
): { label: string; value: string | null; note: string | null } {
  const value = (founded ?? "").trim() || null;
  switch (dateSource) {
    case "rdap":
      return {
        label: "Domain registered",
        value,
        note:
          "An RDAP domain-registration date — domains are often registered years before the "
          + "product exists, so this is not a founding year.",
      };
    case "wayback":
      return {
        label: "First archived",
        value,
        note: "The earliest Wayback snapshot — an approximation, not a founding year.",
      };
    case "llm":
      return {
        label: "Founded (model-drafted)",
        value,
        note: "Drafted by a model from the site. A human has not confirmed this date.",
      };
    case "human":
      return { label: "Founded", value, note: "Confirmed by a human." };
    default:
      return {
        label: "Founded (date source unrecorded)",
        value,
        note: "No date source was recorded for this value, so it is shown as unconfirmed.",
      };
  }
}

/**
 * The card-row form of the same rule. Anything that is not a human-confirmed
 * date is marked as an estimate (`est.`) or an approximation (`≈`) and carries
 * a `title` saying exactly what it is. A null date yields no text at all — the
 * old hardcoded `"2021"` fallback fabricated a vintage, and it is gone.
 */
export function foundedShort(
  founded: string | null | undefined,
  dateSource: LooseDateSource,
): { text: string | null; title: string } {
  const year = (founded ?? "").match(/\d{4}/)?.[0] ?? null;
  if (!year) return { text: null, title: "no dated founding information on this record" };
  switch (dateSource) {
    case "human":
      return { text: `founded ${year}`, title: `${year} — confirmed by a human` };
    case "llm":
      return { text: `\u2248${year}`, title: `${year} drafted by a model from the site — not human-confirmed` };
    case "rdap":
      return { text: `est. ${year}`, title: `${year} is an RDAP domain-registration date, not necessarily the founding year` };
    case "wayback":
      return { text: `est. ${year}`, title: `${year} is the earliest Wayback snapshot — an approximation` };
    default:
      return { text: `est. ${year}`, title: `${year} — no date source recorded, so it is shown as an estimate` };
  }
}

/**
 * Pastel chip colors for initial avatars. One style works in BOTH themes:
 * a light pastel background with a dark same-hue letter passes contrast
 * on beige AND charcoal (dark text on ~78% lightness ≈ 7:1).
 */
export function hueAvatarStyle(name: string): React.CSSProperties {
  const h = hueFromName(name);
  return {
    backgroundColor: `hsl(${h} 55% 78%)`,
    color: `hsl(${h} 60% 26%)`,
  };
}
