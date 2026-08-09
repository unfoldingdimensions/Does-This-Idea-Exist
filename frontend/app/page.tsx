"use client";

import * as React from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import {
  BarChart3,
  BrainCircuit,
  Building2,
  Code2,
  Coins,
  FolderGit2,
  Gamepad2,
  Globe,
  GraduationCap,
  HeartPulse,
  Landmark,
  Megaphone,
  MousePointerClick,
  Palette,
  Plane,
  RefreshCw,
  ServerCrash,
  Share2,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  UtensilsCrossed,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StartupCard } from "@/components/startup-card";
import { AddStartupDialog } from "@/components/add-startup-dialog";
import { AdminPanel } from "@/components/admin-panel";
import { ThemeToggle } from "@/components/theme-toggle";
import { FilterBar } from "@/components/filter-bar";
import { StartupDetail } from "@/components/startup-detail";
import { HomeSections } from "@/components/home-sections";
import { MorphingDiscoveryBar, type DiscoveryCategory } from "@/components/ui/morphing-discovery-bar";
import { SplitButton } from "@/components/ui/split-button";
import { ContinuousPagination } from "@/components/ui/continuous-pagination";
import { fetchStartups, fetchCategories, fetchStats, runVerification, markVerified } from "@/lib/api";
import { CountUp } from "@/components/count-up";
import { filterStartups, sortStartups, foundedYear } from "@/lib/search";
import type { SortKey } from "@/lib/search";
import { formatDate, titleCase } from "@/lib/format";
import type { CategoryCount, Startup, Stats } from "@/lib/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 24;

/** Read filter state from the URL on first client render (SSR-safe: window guard). */
function readInitialParams(): {
  query: string;
  category: string | null;
  year: string;
  status: string;
  sort: SortKey;
  page: number;
} {
  if (typeof window === "undefined") {
    return { query: "", category: null, year: "all", status: "all", sort: "top", page: 1 };
  }
  const p = new URLSearchParams(window.location.search);
  const sort = p.get("sort");
  const rawCategory = p.get("category")?.trim().toLowerCase();
  const rawPage = Number.parseInt(p.get("page") ?? "1", 10);
  return {
    query: p.get("q") ?? "",
    category: rawCategory ? rawCategory : null,
    year: p.get("year") ?? "all",
    status: p.get("status") ?? "all",
    sort: sort === "newest" || sort === "verified" || sort === "name" || sort === "founded" ? sort : "top",
    page: Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1,
  };
}

/** Lucide icon per known category — one icon set (MIT), fallback Sparkles. */
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  ai: <Sparkles className="h-3.5 w-3.5" />,
  "developer-tools": <Code2 className="h-3.5 w-3.5" />,
  design: <Palette className="h-3.5 w-3.5" />,
  fintech: <Landmark className="h-3.5 w-3.5" />,
  productivity: <Zap className="h-3.5 w-3.5" />,
  "machine-learning": <BrainCircuit className="h-3.5 w-3.5" />,
  marketing: <Megaphone className="h-3.5 w-3.5" />,
  "social-media": <Share2 className="h-3.5 w-3.5" />,
  health: <HeartPulse className="h-3.5 w-3.5" />,
  "e-commerce": <ShoppingBag className="h-3.5 w-3.5" />,
  education: <GraduationCap className="h-3.5 w-3.5" />,
  analytics: <BarChart3 className="h-3.5 w-3.5" />,
  "no-code": <MousePointerClick className="h-3.5 w-3.5" />,
  crypto: <Coins className="h-3.5 w-3.5" />,
  gaming: <Gamepad2 className="h-3.5 w-3.5" />,
  food: <UtensilsCrossed className="h-3.5 w-3.5" />,
  travel: <Plane className="h-3.5 w-3.5" />,
  "open-source": <FolderGit2 className="h-3.5 w-3.5" />,
};

function categoryIcon(id: string): React.ReactNode {
  return CATEGORY_ICONS[id] ?? <Sparkles className="h-3.5 w-3.5" />;
}

export default function HomePage() {
  const [startups, setStartups] = React.useState<Startup[]>([]);
  const [categories, setCategories] = React.useState<CategoryCount[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [query, setQuery] = React.useState(() => readInitialParams().query);
  const [category, setCategory] = React.useState<string | null>(() => readInitialParams().category);
  const [year, setYear] = React.useState(() => readInitialParams().year);
  const [status, setStatus] = React.useState(() => readInitialParams().status);
  const [sort, setSort] = React.useState<SortKey>(() => readInitialParams().sort);
  const [page, setPage] = React.useState(() => readInitialParams().page);
  const [loading, setLoading] = React.useState(true);
  const [online, setOnline] = React.useState(true);
  const [verifying, setVerifying] = React.useState(false);
  const [detail, setDetail] = React.useState<Startup | null>(null);
  const [addOpen, setAddOpen] = React.useState(false);
  const [addTab, setAddTab] = React.useState<"github" | "website">("github");
  const [gridRef] = useAutoAnimate({ duration: 260 });

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

  React.useEffect(() => {
    void loadAll();
  }, [loadAll]);

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
    // exact-name match must rank #1 — see review finding #1); an explicit sort
    // choice from the user is still honored over relevance.
    return searching && sort === "top" ? filtered : sortStartups(filtered, sort);
  }, [startups, query, category, year, status, sort]);

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  // Clamp during render (no setState-in-effect): a URL page beyond the last page
  // after filtering shows the last page while `page` state stays untouched.
  const currentPage = Math.min(page, totalPages);
  const paged = React.useMemo(
    () => results.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [results, currentPage],
  );

  // Filter/sort changes reset to page 1 — done in the setters (no effects).
  const changeQuery = (q: string) => {
    setQuery(q);
    setPage(1);
  };
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

  const hasAnyFilter = query !== "" || category !== null || year !== "all" || status !== "all";

  const clearFilters = () => {
    changeQuery("");
    changeCategory(null);
    changeYear("all");
    changeStatus("all");
  };

  // Shareable, back-button-safe URL state: replaceState (never pushState — no history spam)
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const p = new URLSearchParams();
    if (query) p.set("q", query);
    if (category) p.set("category", category);
    if (year !== "all") p.set("year", year);
    if (status !== "all") p.set("status", status);
    if (sort !== "top") p.set("sort", sort);
    if (currentPage > 1) p.set("page", String(currentPage));
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [query, category, year, status, sort, currentPage]);

  const handleAdded = (entry: Startup) => {
    setStartups((prev) => {
      const without = prev.filter(
        (s) =>
          s.id !== entry.id &&
          s.website_url !== entry.website_url &&
          s.github_url !== entry.github_url,
      );
      return sortStartups([...without, entry]);
    });
    setQuery("");
    setCategory(null);
    setPage(1);
    void loadAll();
  };

  const handleVerify = async () => {
    if (verifying) return;
    setVerifying(true);
    try {
      const r = await runVerification();
      toast.success(`Verified ${r.ok}/${r.checked} · ${r.flagged} flagged`, {
        description:
          r.dead_flipped.length > 0
            ? `Archived: ${r.dead_flipped.join(", ")}`
            : "No dead entries flipped.",
      });
      await loadAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setVerifying(false);
    }
  };

  const handleMarkVerified = async (s: Startup) => {
    try {
      const updated = await markVerified(s.id);
      toast.success(`${updated.name} marked verified`);
      setStartups((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setDetail((d) => (d && d.id === updated.id ? updated : d)); // keep the open modal in sync
      void loadAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to mark verified");
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
      {/* Header — frosted glass */}
      <header className="sticky top-0 z-40 border-b border-border/40 bg-background/55 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <span className="font-display text-sm font-bold tracking-tight">IdeaExists</span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Does this startup exist?
          </span>
          <div className="ml-auto flex items-center gap-2">
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
            <ThemeToggle />
          </div>
        </div>
      </header>

      {!online && !loading && (
        <div className="flex items-center justify-center gap-2 border-b border-border/40 bg-destructive/5 px-4 py-2 text-xs text-destructive">
          <ServerCrash className="h-3.5 w-3.5" />
          The archive is unreachable — start it with{" "}
          <code className="font-mono">uvicorn app.main:app --port 8020</code>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-20">
        {/* Hero */}
        <section className="mx-auto max-w-3xl pb-10 pt-12 text-center">
          <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
            A human-kept archive of what exists.
          </h1>
          <p className="mx-auto mt-3 max-w-[52ch] text-sm text-muted-foreground">
            Search the archive — what they do, where they live, and whether they&rsquo;re still alive.
            Every listing checked by a human, not a crawler.
          </p>

          <div className="mt-7">
            <MorphingDiscoveryBar
              categories={discoveryCategories}
              value={category}
              onCategoryChange={changeCategory}
              query={query}
              onQueryChange={changeQuery}
              totalCount={stats?.total}
            />
          </div>

          {/* Freshness + trust — one muted ledger line under the bar (the bar
              itself carries the live count as "All 94"). Distilled from the
              former three-band hero per critique P2. */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 font-mono text-[10px] text-muted-foreground">
            {stats?.last_checked && (
              <span className="tabular-nums">last checked {formatDate(stats.last_checked)}</span>
            )}
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden />
              Verified — a human checked it
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" aria-hidden />
              Unverified — filed, awaiting a human
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-destructive/80" aria-hidden />
              Dead — checked, gone
            </span>
          </div>
        </section>

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
        />

        {/* Freshness highlights — only on the unfiltered landing view */}
        {!hasAnyFilter && !loading && results.length > 0 && (
          <HomeSections startups={startups} onNavigate={setDetail} />
        )}

        {/* Grid */}
        {loading ? (
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="glass h-48 rounded-2xl" />
            ))}
          </div>
        ) : paged.length === 0 ? (
          <div className="glass mx-auto max-w-md rounded-2xl px-6 py-12 text-center">
            <Building2 className="mx-auto h-8 w-8 text-muted-foreground" />
            <h2 className="mt-3 text-sm font-bold">
              {hasAnyFilter ? "Nothing in the archive matches." : "Nothing on file yet."}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {hasAnyFilter
                ? "Try widening the net — or file it yourself. The archive grows with every seed."
                : "Either it doesn't exist — or you're about to be the first to file it."}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {hasAnyFilter && (
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              )}
              <Button size="sm" className="gap-1.5" onClick={() => setAddOpen(true)}>
                <Sparkles className="h-3.5 w-3.5" /> Add it to the archive
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div
              ref={gridRef}
              className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]"
            >
              {paged.map((s) => (
                <StartupCard
                  key={s.id}
                  startup={s}
                  onVerified={handleMarkVerified}
                  onDetails={setDetail}
                />
              ))}
            </div>
            <ContinuousPagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )}

        {/* Detail modal — shared-layout expansion */}
        <StartupDetail
          startup={detail}
          startups={startups}
          onClose={() => setDetail(null)}
          onNavigate={setDetail}
          onVerified={handleMarkVerified}
        />

        {/* Add dialog — controlled by split-button / empty state */}
        <AddStartupDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          tab={addTab}
          onTabChange={setAddTab}
          onAdded={handleAdded}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-background/55 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            {online ? (
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
            ) : (
              <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
            )}
            <span className="font-mono text-[11px] tabular-nums">
              <CountUp value={stats?.total ?? 0} /> startups
            </span>
          </span>
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="font-mono text-[11px] tabular-nums">
              <CountUp value={stats?.verified ?? 0} /> verified
            </span>
          </span>
          <span className="hidden font-mono text-[11px] tabular-nums md:inline">
            Dead is a status, not an erasure. Kept by a human, checked weekly.
          </span>
          <span className="hidden lg:inline">
            No accounts. No tracking. Searches stay on this machine.
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <AdminPanel onSeeded={() => void loadAll()} />
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1.5 text-xs"
              onClick={handleVerify}
              disabled={verifying || !online}
            >
              <RefreshCw className={cn("h-3 w-3", verifying && "animate-spin")} />
              Run verification
            </Button>
          </div>
        </div>
      </footer>
    </div>
  );
}
