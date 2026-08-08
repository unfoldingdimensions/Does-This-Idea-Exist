"use client";

import * as React from "react";
import { Search, ShieldCheck, RefreshCw, ServerCrash, Building2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StartupCard } from "@/components/startup-card";
import { AddStartupDialog } from "@/components/add-startup-dialog";
import { ThemeToggle } from "@/components/theme-toggle";
import { fetchStartups, fetchCategories, fetchStats, runVerification, markVerified } from "@/lib/api";
import { filterStartups, sortStartups } from "@/lib/search";
import { titleCase } from "@/lib/format";
import type { CategoryCount, Startup, Stats } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const [startups, setStartups] = React.useState<Startup[]>([]);
  const [categories, setCategories] = React.useState<CategoryCount[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [online, setOnline] = React.useState(true);
  const [verifying, setVerifying] = React.useState(false);

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

  // Debounced client-side search (dataset is small — no backend round-trip per keystroke)
  const results = React.useMemo(() => {
    const base = category ? startups.filter((s) => s.category === category) : startups;
    return filterStartups(base, query);
  }, [startups, query, category]);

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
      void loadAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to mark verified");
    }
  };

  return (
    <div className="flex min-h-full flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <span className="text-sm font-bold tracking-tight">IdeaExists</span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Does this startup exist?
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <AddStartupDialog onAdded={handleAdded} />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {!online && !loading && (
        <div className="flex items-center justify-center gap-2 border-b bg-destructive/5 px-4 py-2 text-xs text-destructive">
          <ServerCrash className="h-3.5 w-3.5" />
          Backend offline — start it with <code className="font-mono">uvicorn app.main:app --port 8020</code>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-20">
        {/* Hero + search */}
        <section className="mx-auto max-w-2xl pb-9 pt-12 text-center">
          <h1 className="text-3xl font-bold tracking-tight">
            Does this startup exist?
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Searchable directory of startups — what they do, their website, their code.
          </p>
          <div className="relative mx-auto mt-6 max-w-xl">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. AI resume builder for developers"
              className="h-10 rounded-lg pl-9"
              aria-label="Search startups"
            />
          </div>
        </section>

        {/* Category chips */}
        {categories.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 pb-9">
            <button
              onClick={() => setCategory(null)}
              className={cn(
                "h-7 rounded-full px-3 text-xs font-medium transition-colors",
                category === null
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              All
            </button>
            {categories.map((c) => (
              <button
                key={c.category}
                onClick={() => setCategory(category === c.category ? null : c.category)}
                className={cn(
                  "h-7 rounded-full px-3 text-xs font-medium transition-colors",
                  category === c.category
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                {titleCase(c.category)} <span className="opacity-60">{c.count}</span>
              </button>
            ))}
          </div>
        )}

        {/* Grid */}
        {loading ? (
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-48 rounded-xl" />
            ))}
          </div>
        ) : results.length === 0 ? (
          <div className="mx-auto max-w-md rounded-xl bg-muted/40 px-6 py-12 text-center">
            <Building2 className="mx-auto h-8 w-8 text-muted-foreground" />
            <h2 className="mt-3 text-sm font-bold">Nothing found for “{query || "this filter"}”</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Maybe <span className="font-medium">you</span> build this? Add it to the directory
              and check back next week.
            </p>
            <div className="mt-4 flex justify-center">
              <AddStartupDialog onAdded={handleAdded} />
            </div>
          </div>
        ) : (
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
            {results.map((s) => (
              <StartupCard key={s.id} startup={s} onVerified={handleMarkVerified} />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            {online ? (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            ) : (
              <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
            )}
            {stats?.total ?? 0} startups
          </span>
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            {stats?.verified ?? 0} verified
          </span>
          {stats?.last_checked && <span>Last checked {stats.last_checked.slice(0, 10)}</span>}
          <span className="hidden md:inline">
            Links re-verified weekly · 3 failed checks → archived (never deleted)
          </span>
          <Button
            variant="outline"
            size="sm"
            className="ml-auto h-7 gap-1.5 text-xs"
            onClick={handleVerify}
            disabled={verifying || !online}
          >
            <RefreshCw className={cn("h-3 w-3", verifying && "animate-spin")} />
            Run verification
          </Button>
        </div>
      </footer>
    </div>
  );
}
