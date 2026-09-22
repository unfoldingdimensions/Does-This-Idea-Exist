"use client";

import * as React from "react";
import {
  Archive,
  Briefcase,
  Code2,
  Film,
  FolderGit2,
  Globe,
  GraduationCap,
  HeartPulse,
  Landmark,
  Monitor,
  PackageOpen,
  ServerCrash,
  Share2,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Zap,
  Command,
} from "lucide-react";
import { toast } from "sonner";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { EASE } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { CardSkeleton, LedgerRowSkeleton } from "@/components/card-skeleton";
import { StartupCard, type StatusChoice } from "@/components/startup-card";
import { AddStartupDialog } from "@/components/add-startup-dialog";
import { AdminPanel } from "@/components/admin-panel";
import { ThemeToggle } from "@/components/theme-toggle";
import { scrollPageToTop } from "@/components/scroll-utils";
import { FilterBar } from "@/components/filter-bar";
import { StartupDetail } from "@/components/startup-detail";
import { HomeSections } from "@/components/home-sections";
import { MorphingDiscoveryBar, type DiscoveryCategory } from "@/components/ui/morphing-discovery-bar";
import { SplitButton } from "@/components/ui/split-button";
import { ContinuousPagination } from "@/components/ui/continuous-pagination";
import {
  fetchStartups,
  fetchCategories,
  fetchStats,
  markVerified,
  markUnverified,
  markDead,
  searchStartups,
} from "@/lib/api";
import { KineticMasthead } from "@/components/kinetic-masthead";
import { LiveTelemetryBar } from "@/components/live-telemetry-bar";
import { AudioToggle } from "@/components/audio-toggle";
import { DensityToggle, type DensityMode } from "@/components/density-toggle";
import { OdometerNumber } from "@/components/ui/odometer-number";
import { CommandPalette } from "@/components/ui/command-palette";
import { ArchivalTicker } from "@/components/ui/archival-ticker";
import { LedgerTableHeader } from "@/components/ledger-table-header";
import { EmptyState } from "@/components/ui/empty-state";
import { sound } from "@/lib/sound-engine";
import { filterStartups, sortStartups, foundedYear } from "@/lib/search";
import type { SortKey } from "@/lib/search";
import { formatDate, foundedShort, titleCase } from "@/lib/format";
import { useAdminToken } from "@/lib/use-admin-token";
import type { CategoryCount, Startup, Stats } from "@/lib/types";

const PAGE_SIZE = 24;

/** Read filter state from the URL (client-only — called from a mount effect). */
function readInitialParams(): {
  query: string;
  category: string | null;
  year: string;
  status: string;
  sort: SortKey;
  page: number;
} {
  const p = new URLSearchParams(window.location.search);
  const sort = p.get("sort");
  const rawCategory = p.get("category")?.trim().toLowerCase();
  const rawPage = Number.parseInt(p.get("page") ?? "1", 10);
  // Whitelist deep-linked facet values: a stale ?status=bogus (or a year that
  // no longer exists — self-healed after load) would otherwise render a blank
  // Select with an active Clear button that filters nothing.
  const rawStatus = p.get("status") ?? "all";
  const status = ["all", "verified", "unverified", "dead"].includes(rawStatus)
    ? rawStatus
    : "all";
  return {
    query: p.get("q") ?? "",
    category: rawCategory ? rawCategory : null,
    year: p.get("year") ?? "all",
    status,
    sort: sort === "newest" || sort === "verified" || sort === "name" || sort === "founded" ? sort : "top",
    page: Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1,
  };
}

/** Lucide icon per known category — mirrors the backend whitelist
 * (enrich.CATEGORIES): productivity, ai, devtools, desktop, freelance,
 * finance, health, education, ecommerce, social, media, other. Unknown →
 * Sparkles fallback (kept in sync with the LLM prompt's enum). */
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  ai: <Sparkles className="h-3.5 w-3.5" />,
  devtools: <Code2 className="h-3.5 w-3.5" />,
  desktop: <Monitor className="h-3.5 w-3.5" />,
  freelance: <Briefcase className="h-3.5 w-3.5" />,
  finance: <Landmark className="h-3.5 w-3.5" />,
  productivity: <Zap className="h-3.5 w-3.5" />,
  health: <HeartPulse className="h-3.5 w-3.5" />,
  education: <GraduationCap className="h-3.5 w-3.5" />,
  ecommerce: <ShoppingBag className="h-3.5 w-3.5" />,
  social: <Share2 className="h-3.5 w-3.5" />,
  media: <Film className="h-3.5 w-3.5" />,
  // "Other" must read as distinct from AI's Sparkles (both hit the fallback
  // before — same icon on two chips, indistinguishable at a glance).
  other: <PackageOpen className="h-3.5 w-3.5" />,
};

function categoryIcon(id: string): React.ReactNode {
  return CATEGORY_ICONS[id] ?? <Sparkles className="h-3.5 w-3.5" />;
}

export default function HomePage() {
  const [startups, setStartups] = React.useState<Startup[]>([]);
  const [categories, setCategories] = React.useState<CategoryCount[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState<string | null>(null);
  const [year, setYear] = React.useState("all");
  const [status, setStatus] = React.useState("all");
  const [sort, setSort] = React.useState<SortKey>("top");
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [online, setOnline] = React.useState(true);
  const [detail, setDetail] = React.useState<Startup | null>(null);
  const [addOpen, setAddOpen] = React.useState(false);
  const [addTab, setAddTab] = React.useState<"github" | "website">("github");
  const [density, setDensity] = React.useState<DensityMode>("gallery");
  const [cmdOpen, setCmdOpen] = React.useState(false);
  // Id → the server's frozen match reason for the current query (F-18).
  const [reasons, setReasons] = React.useState<Map<number, string>>(new Map());
  const unlocked = useAdminToken() !== null;
  const reduce = useReducedMotion();

  // Deep-linked filters (?q=…&page=…) are applied AFTER mount. Reading them in
  // useState initializers made the first client render disagree with the
  // server prerender (hydration prop mismatch on the search input). State
  // starts at server defaults; urlApplied gates the replaceState effect so it
  // can't wipe the URL first. The setStates run in a microtask — the project's
  // react-hooks rule forbids synchronous setState in effect bodies, and the
  // microtask still fires before the browser can paint or navigate.
  const [urlApplied, setUrlApplied] = React.useState(false);
  React.useEffect(() => {
    void Promise.resolve().then(() => {
      const init = readInitialParams();
      setQuery(init.query);
      setCategory(init.category);
      setYear(init.year);
      setStatus(init.status);
      setSort(init.sort);
      setPage(init.page);
      setUrlApplied(true);
    });
  }, []);

  // Header firms up after the page scrolls past a 1px sentinel (one
  // IntersectionObserver, not a second useScroll rig). No height change —
  // the header is in flow and scroll-triggered shifts count toward CLS.
  const [scrolled, setScrolled] = React.useState(false);
  React.useEffect(() => {
    const sentinel = document.createElement("div");
    sentinel.style.position = "absolute";
    sentinel.style.top = "0";
    sentinel.style.height = "1px";
    sentinel.style.width = "1px";
    document.body.prepend(sentinel);
    const io = new IntersectionObserver(
      ([entry]) => setScrolled(!entry.isIntersecting),
      { threshold: 0 },
    );
    io.observe(sentinel);
    return () => {
      io.disconnect();
      sentinel.remove();
    };
  }, []);

  const loadAll = React.useCallback(() => {
    // setState only inside .then callbacks (react-hooks v7: no synchronous setState in effects)
    return Promise.allSettled([
      fetchStartups(),
      fetchCategories(),
      fetchStats(),
    ]).then(([s, c, st]) => {
      if (s.status === "fulfilled") {
        setStartups(s.value);
        setOnline(true);
      } else {
        setOnline(false);
      }
      if (c.status === "fulfilled") setCategories(c.value);
      if (st.status === "fulfilled") setStats(st.value);
      setLoading(false);
    });
  }, []);

  // Status toggles already patch the row in place — only the counters move.
  // Refetching 225 KiB of archive per stamp was the pre-refactor behavior.
  const refreshCounts = React.useCallback(() => {
    return Promise.allSettled([fetchCategories(), fetchStats()]).then(([c, st]) => {
      if (c.status === "fulfilled") setCategories(c.value);
      if (st.status === "fulfilled") setStats(st.value);
    });
  }, []);

  // Truncation is detectable on the wire: the list fetch carries no limit, so
  // startups.length < stats.total means the ceiling bit (HTTP 200, short body,
  // no error). Banner it honestly with both real numbers — and only when the
  // archive is actually reachable, so a failed fetch can't make it lie.
  const truncated = online && !loading && startups.length < (stats?.total ?? 0);

  React.useEffect(() => {
    void loadAll();
  }, [loadAll]);

  // Search reasons (item 6). The FILTERING stays on the client: `lib/search.ts`
  // (Fuse, exact-name first, dead last, stars as a tie-break) is pleasant to
  // ~3,000 rows at ~22ms/term, while /api/search measures ~83-123ms per query
  // over the 1,300-row archive. So this endpoint is used for what it is better
  // at — the server's own per-result `reason` — and is debounced harder than
  // the input itself (300ms vs 150ms), because it must never gate a keystroke.
  // A failure here is additive-only: the grid keeps its client-side matches and
  // simply loses the reason line, rather than emptying the archive.
  React.useEffect(() => {
    const q = query.trim();
    if (!q) {
      // Not called synchronously in the effect body (react-hooks v7).
      void Promise.resolve().then(() =>
        setReasons((prev) => (prev.size === 0 ? prev : new Map())),
      );
      return undefined;
    }
    const t = window.setTimeout(() => {
      searchStartups(q)
        .then((rows) => setReasons(new Map(rows.map((r) => [r.id, r.reason]))))
        .catch(() => setReasons(new Map()));
    }, 300);
    return () => window.clearTimeout(t);
  }, [query]);

  // Stable identity for AdminPanel's onSeeded — an inline lambda here changed
  // on every render and cascaded new callback identities into the admin
  // polling chain (interval teardown, HealthCheckSection effect churn).
  const handleSeeded = React.useCallback(() => void loadAll(), [loadAll]);

  // Debounced client-side search + facets (dataset is small — no backend round-trip per keystroke)
  const results = React.useMemo(() => {
    const filtered = filterStartups(startups, {
      q: query,
      category,
      year: year === "all" ? null : year,
      status: status === "all" ? null : status,
    });
    const searching = query.trim().length > 0;
    // While searching on the default sort, keep Fuse's relevance ranking (the
    // exact-name match must rank #1 — see review finding #1). The sort select
    // mirrors this: it offers "Relevance" instead of "Top (stars)" (a no-op
    // mapping), and picking any other sort key exits relevance mode.
    return searching && sort === "top" ? filtered : sortStartups(filtered, sort);
  }, [startups, query, category, year, status, sort]);

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  // Clamp during render (no setState-in-effect): a URL page beyond the last page
  // after filtering shows the last page. While loading, keep the raw deep-linked
  // page so ?page=5 survives the empty-results skeleton.
  const currentPage = loading ? page : Math.min(page, totalPages);
  // Self-heal `page` to the clamp (React's adjust-state-during-render): without
  // it the stale value resurfaces when filters later widen totalPages again.
  if (!loading && page !== currentPage) setPage(currentPage);
  const paged = React.useMemo(
    () => results.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [results, currentPage],
  );

  // Page switch = content swap + glide back to the top, so the reader never
  // lands mid-page (pagination sits at the bottom; without the scroll the next
  // page opens at its own bottom — reported jank). Driven through Lenis so the
  // glide matches the app's inertial feel; instant under reduced motion.
  const changePage = (p: number) => {
    if (p === currentPage) return;
    setPage(p);
    scrollPageToTop();
  };

  // Filter/sort changes reset to page 1 — done in the setters (no effects).
  // Typing is debounced: Fuse over the archive is ~20ms/term and rebuilding its
  // index per keystroke measured 120-180ms of input jank. Clearing is instant.
  const queryTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const changeQuery = (q: string) => {
    if (q === "") {
      if (queryTimer.current) clearTimeout(queryTimer.current);
      setQuery("");
      setPage(1);
      return;
    }
    if (queryTimer.current) clearTimeout(queryTimer.current);
    queryTimer.current = setTimeout(() => {
      setQuery(q);
      setPage(1);
    }, 150);
  };
  React.useEffect(
    () => () => {
      if (queryTimer.current) clearTimeout(queryTimer.current);
    },
    [],
  );
  const changeCategory = (c: string | null) => {
    setCategory(c);
    setPage(1);
  };
  const changeYear = (y: string) => {
    setYear(y);
    setPage(1);
  };
  const changeStatus = (s: string) => {
    setStatus(s);
    setPage(1);
  };
  const changeSort = (k: SortKey) => {
    setSort(k);
    setPage(1);
  };

  const years = React.useMemo(() => {
    const set = new Set<string>();
    startups.forEach((s) => {
      const y = foundedYear(s.founded);
      if (y) set.add(y);
    });
    return [...set].sort((a, b) => b.localeCompare(a));
  }, [startups]);
  // Self-heal a deep-linked ?year= that exists in no filing (stale link):
  // a Select value with no matching item renders blank while looking active.
  if (!loading && year !== "all" && !years.includes(year)) setYear("all");

  // Same-name filings (e.g. Bird filed twice — genuinely different companies
  // that share a name). The archive admits the overlap instead of hiding it.
  const nameCounts = React.useMemo(() => {
    const counts = new Map<string, number>();
    startups.forEach((s) => counts.set(s.name, (counts.get(s.name) ?? 0) + 1));
    return counts;
  }, [startups]);

  const hasAnyFilter = query !== "" || category !== null || year !== "all" || status !== "all";

  // Easter egg #1 — the self-referential query: asking whether this product
  // exists gets the archive's own Verified pill. It IS the thesis.
  const selfQuery = /^(does this startup exist|ideaexists|is this a real startup)$/i.test(
    query.trim(),
  );

  // Easter egg #2 — the Curator signs off after three clicks on the footer
  // mantra. Deliberately a plain <span onClick> with no role: adding a tab
  // stop for a joke is worse accessibility than leaving it mouse-only.
  const mantraRef = React.useRef({ count: 0, last: 0 });
  const handleMantraClick = () => {
    const now = Date.now();
    const r = mantraRef.current;
    r.count = now - r.last > 1500 ? 1 : r.count + 1;
    r.last = now;
    if (r.count >= 3) {
      r.count = 0;
      toast("Filed honestly. Re-checked on a schedule. — The Curator");
    }
  };

  const clearFilters = () => {
    changeQuery("");
    changeCategory(null);
    changeYear("all");
    changeStatus("all");
  };

  // Global keyboard shortcut: press "/" to focus the archive search input.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key !== "/" ||
        e.ctrlKey ||
        e.metaKey ||
        e.altKey ||
        // Never yank focus behind an open modal/dialog: with a scroll-locked
        // page the input is under the backdrop, and typing into an invisible
        // field is exactly the failure this guard exists to prevent.
        document.body.style.overflow === "hidden" ||
        (e.target instanceof HTMLElement &&
          ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName))
      )
        return;
      e.preventDefault();
      const input = document.querySelector<HTMLInputElement>(
        "input[aria-label='Search startups']",
      );
      input?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Shareable, back-button-safe URL state: replaceState (never pushState — no history spam).
  // Gated on urlApplied so the first pass can't wipe a deep-linked ?q=… before
  // the mount effect above has read it.
  React.useEffect(() => {
    if (typeof window === "undefined" || !urlApplied) return;
    const p = new URLSearchParams();
    if (query) p.set("q", query);
    if (category) p.set("category", category);
    if (year !== "all") p.set("year", year);
    if (status !== "all") p.set("status", status);
    if (sort !== "top") p.set("sort", sort);
    if (currentPage > 1) p.set("page", String(currentPage));
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [urlApplied, query, category, year, status, sort, currentPage]);

  const handleAdded = (entry: Startup) => {
    setStartups((prev) => {
      // Null URLs must not match each other — a GitHub-only entry (null
      // website_url) would otherwise evict every other null-website row.
      const without = prev.filter(
        (s) =>
          s.id !== entry.id &&
          (!entry.website_url || s.website_url !== entry.website_url) &&
          (!entry.github_url || s.github_url !== entry.github_url),
      );
      return sortStartups([...without, entry]);
    });
    setQuery("");
    setCategory(null);
    setPage(1);
    void refreshCounts();
  };

  const handleStatusChange = async (s: Startup, choice: StatusChoice) => {
    try {
      const updated =
        choice === "verified"
          ? await markVerified(s.id)
          : choice === "unverified"
            ? await markUnverified(s.id)
            : await markDead(s.id);
      toast.success(
        choice === "dead"
          ? `${updated.name} — filed. Checked three times, gone.`
          : choice === "unverified"
            ? `${updated.name} — stamp cleared. Back to unverified.`
            : `${updated.name} — checked and alive.`,
        choice === "verified" ? { description: "Stamped today. Reversible." } : undefined,
      );
      setStartups((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setDetail((d) => (d && d.id === updated.id ? updated : d)); // keep the open modal in sync
      void refreshCounts();
    } catch (err) {
      toast.error("The stamp didn't take", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const discoveryCategories: DiscoveryCategory[] = React.useMemo(
    () =>
      [...categories]
        .sort((a, b) => b.count - a.count)
        .map((c) => ({
          id: c.category.toLowerCase(),
          label: titleCase(c.category),
          icon: categoryIcon(c.category.toLowerCase()),
          count: c.count,
        })),
    [categories],
  );

  return (
    <div className="flex min-h-full flex-col">
      {/* Accessible skip-link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-3 focus:py-1.5 focus:text-xs focus:text-primary-foreground focus:shadow-lg focus:outline-hidden focus:ring-2 focus:ring-ring"
      >
        Skip to archival records
      </a>

      {/* Header — frosted glass; firms up under scroll (data-scrolled) */}
      <header
        data-scrolled={scrolled || undefined}
        className="sticky top-0 z-40 border-b border-border/40 bg-background/55 backdrop-blur-xl transition-colors duration-300 data-[scrolled]:border-border/70 data-[scrolled]:bg-background/80"
      >
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <span className="font-display text-sm font-bold tracking-tight">IdeaExists</span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Does this startup exist?
          </span>
          <div className="ml-auto flex items-center gap-2">
            {/* Seeding needs the owner token — hidden rather than shown-and-403ing. */}
            {unlocked && (
              <SplitButton
                mainLabel="Add startup"
                options={[
                  {
                    label: "By GitHub",
                    icon: <FolderGit2 className="h-3.5 w-3.5" />,
                    onClick: () => {
                      setAddTab("github");
                      setAddOpen(true);
                    },
                  },
                  {
                    label: "By website",
                    icon: <Globe className="h-3.5 w-3.5" />,
                    onClick: () => {
                      setAddTab("website");
                      setAddOpen(true);
                    },
                  },
                ]}
              />
            )}
            <Button
              variant="outline"
              size="xs"
              onClick={() => {
                sound.playTick();
                setCmdOpen(true);
              }}
              className="hidden sm:inline-flex h-8 gap-1.5 rounded-full px-3 text-xs font-mono cursor-pointer hover:border-primary/50"
              title="Open Command Palette (Cmd+K)"
            >
              <Command className="size-3" />
              <span>Search</span>
              <kbd className="rounded border border-border/70 bg-muted px-1 py-0.2 text-[9px] text-muted-foreground">⌘K</kbd>
            </Button>
            <AudioToggle />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {!online && !loading && (
        <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2">
          <div
            role="status"
            className="glass-strong flex items-center gap-2 rounded-full py-2 pl-4 pr-2 text-xs text-destructive shadow-xl"
          >
            <ServerCrash className="h-3.5 w-3.5 shrink-0" />
            <span>The archive is unreachable.</span>
            {process.env.NODE_ENV !== "production" && (
              <code className="hidden font-mono text-[10px] text-muted-foreground sm:inline">
                uvicorn app.main:app --port 8020
              </code>
            )}
            <Button
              variant="outline"
              size="xs"
              onClick={() => {
                setLoading(true);
                void loadAll();
              }}
            >
              Retry
            </Button>
          </div>
        </div>
      )}

      <main id="main-content" className="mx-auto w-full max-w-6xl flex-1 px-4 pb-20">
        {/* Kinetic Hero */}
        <section className="mx-auto max-w-4xl pb-8 pt-6 text-center">
          <KineticMasthead />

          <LiveTelemetryBar stats={stats} className="mt-4 mb-6" />

          <div className="mt-2">
            <MorphingDiscoveryBar
              categories={discoveryCategories}
              value={category}
              onCategoryChange={changeCategory}
              query={query}
              onQueryChange={changeQuery}
              totalCount={stats?.total}
            />
          </div>

          {/* Magic UI Monospace Archival Ticker. Everything on it comes from
              the record: the old feed fabricated a `"2021"` vintage for a null
              date, a `"FinTech"` category for a null category, and stamped
              VERIFIED on every row including the dead ones. */}
          <ArchivalTicker
            items={startups.slice(0, 12).map((s) => ({
              name: s.name,
              category: s.category ? titleCase(s.category) : undefined,
              vintage: foundedShort(s.founded, s.date_source).text?.match(/\d{4}/)?.[0],
              status:
                s.status === "dead" || s.status === "pivoted"
                  ? ("filed" as const)
                  : s.verified === 1
                    ? ("verified" as const)
                    : ("unverified" as const),
            }))}
            onSelectItem={(name) => {
              changeQuery(name);
            }}
            className="mt-4 rounded-xl border border-border/40"
          />

          {/* Freshness + trust — one muted ledger line under the bar (the bar
              itself carries the live count as "All 94"). Distilled from the
              former three-band hero per critique P2. */}
          <div
            className="reveal mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 font-mono text-[10px] text-muted-foreground"
            style={{ animationDelay: "240ms" }}
          >
            {stats?.last_checked && (
              <span className="tabular-nums">last checked {formatDate(stats.last_checked)}</span>
            )}
            <span className="flex items-center gap-1.5">
              <span className="live-dot h-1.5 w-1.5 rounded-full bg-success" aria-hidden />
              Verified — human-checked or machine-approved, stamped on the record
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" aria-hidden />
              Unverified — filed, not yet stamped
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-destructive/80" aria-hidden />
              Dead — checked, gone
            </span>
          </div>
        </section>

        {/* Exhibition Density & Filter Bar controls */}
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Exhibition
            </span>
            <DensityToggle value={density} onChange={setDensity} />
          </div>
        </div>

        {/* Filter bar: count, founded-year, status, sort */}
        <FilterBar
          sort={sort}
          onSort={changeSort}
          year={year}
          onYear={changeYear}
          status={status}
          onStatus={changeStatus}
          years={years}
          count={results.length}
          onClear={clearFilters}
          showClear={hasAnyFilter}
          searching={query.trim().length > 0}
        />

        {/* Truncation banner — the ceiling bit and the frontend knows it */}
        {truncated && (
          <div
            role="status"
            className="mb-4 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 rounded-xl border border-border/40 bg-background/60 px-4 py-2 text-xs text-muted-foreground"
          >
            <Archive className="h-3.5 w-3.5 shrink-0" />
            <span>
              Showing {startups.length.toLocaleString()} of {stats!.total.toLocaleString()} filings —
              search and filters only cover the {startups.length.toLocaleString()} shown.
            </span>
          </div>
        )}

        {/* Freshness highlights — only on the unfiltered landing view */}
        <AnimatePresence>
          {!hasAnyFilter && !loading && results.length > 0 && (
            <motion.div
              key="home-sections"
              initial={{ opacity: 0, y: reduce ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={
                reduce ? { duration: 0 } : { type: "tween", ease: EASE, duration: 0.25 }
              }
            >
              <HomeSections startups={startups} onNavigate={setDetail} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Grid or Ledger View */}
        {loading ? (
          density === "ledger" ? (
            <div className="flex flex-col gap-2">
              <LedgerTableHeader />
              {Array.from({ length: 12 }).map((_, i) => (
                <LedgerRowSkeleton key={i} />
              ))}
            </div>
          ) : (
            <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
              {Array.from({ length: 12 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          )
        ) : selfQuery ? (
          <div className="glass mx-auto max-w-md rounded-2xl px-6 py-12 text-center">
            <ShieldCheck className="mx-auto h-8 w-8 text-success" />
            <h2 className="mt-3 text-sm font-bold">Yes. You&rsquo;re looking at it.</h2>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              The thing you&rsquo;re asking about is the page you&rsquo;re on — an
              archive of what exists, with each stamp&rsquo;s provenance on the
              record.
            </p>
            <div className="mt-4 flex justify-center">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-success/25 bg-success/12 px-2.5 py-0.5 text-[11px] font-medium text-success dark:bg-success/15">
                <span className="size-1.5 rounded-full bg-success" aria-hidden />
                <ShieldCheck className="h-3 w-3" /> Verified
              </span>
            </div>
          </div>
        ) : paged.length === 0 ? (
          <EmptyState
            title={hasAnyFilter ? "NO ARCHIVAL FILINGS MATCH CRITERIA" : "ARCHIVAL VAULT EMPTY"}
            description={
              hasAnyFilter
                ? "The vault scanned all active and historical startups, but found zero records matching your active filters."
                : "No entities have been filed in this partition yet."
            }
            onResetFilters={hasAnyFilter ? clearFilters : undefined}
            onOpenSubmit={unlocked ? () => setAddOpen(true) : undefined}
          />
        ) : (
          <>
            {density === "ledger" && <LedgerTableHeader />}
            <div
              className={
                density === "ledger"
                  ? "flex flex-col gap-2"
                  : "grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]"
              }
            >
              {paged.map((s, i) => (
                <div
                  key={s.id}
                  className="deal-item"
                  style={
                    {
                      "--i": i,
                      "--deal-tilt": density === "ledger" ? "0deg" : i % 2 === 0 ? "-0.7deg" : "0.7deg",
                    } as React.CSSProperties
                  }
                >
                  <StartupCard
                    startup={s}
                    onStatusChange={handleStatusChange}
                    onDetails={setDetail}
                    onSearchName={changeQuery}
                    filings={nameCounts.get(s.name) ?? 1}
                    density={density}
                    reason={query.trim() ? reasons.get(s.id) : undefined}
                  />
                </div>
              ))}
            </div>
            <ContinuousPagination currentPage={currentPage} totalPages={totalPages} onPageChange={changePage} />
          </>
        )}

        {/* Detail modal — shared-layout expansion */}
        <StartupDetail
          startup={detail}
          startups={startups}
          onClose={() => setDetail(null)}
          onNavigate={setDetail}
          onStatusChange={handleStatusChange}
        />

        {/* Add dialog — controlled by split-button / empty state */}
        <AddStartupDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          tab={addTab}
          onTabChange={setAddTab}
          onAdded={handleAdded}
        />

        {/* Command Palette (Cmd+K / Ctrl+K) */}
        <CommandPalette
          open={cmdOpen}
          onOpenChange={setCmdOpen}
          startups={startups}
          onSelectStartup={setDetail}
          onToggleDensity={() => {
            setDensity((d) => (d === "gallery" ? "ledger" : "gallery"));
          }}
          onToggleSound={() => {
            sound.toggleMute();
          }}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-background/55 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            {online ? (
              <span className="live-dot h-1.5 w-1.5 rounded-full bg-success" />
            ) : (
              <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
            )}
            <span className="font-mono text-[11px] tabular-nums">
              <OdometerNumber value={stats?.total ?? 0} /> startups
            </span>
          </span>
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="font-mono text-[11px] tabular-nums">
              <OdometerNumber value={stats?.verified ?? 0} /> verified
            </span>
          </span>
          <span
            className="hidden font-mono text-[11px] tabular-nums md:inline"
            onClick={handleMantraClick}
          >
            Dead is a status, not an erasure. Filed honestly, re-checked on a schedule.
          </span>
          <span className="hidden lg:inline">
            No accounts. No tracking. Searches stay on this machine.
          </span>
          {/* Discoverability for the founder half of the product: the comparison
              lives on a filing's own record page, so say where to find it
              rather than inventing a compare button with nothing to compare. */}
          <span className="hidden xl:inline">
            Founders: every filing has a record page — compare your app against it there.
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <AdminPanel onSeeded={handleSeeded} />
          </div>
        </div>
      </footer>
    </div>
  );
}
