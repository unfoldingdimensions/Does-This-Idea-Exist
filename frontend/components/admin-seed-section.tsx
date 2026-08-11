"use client";

import * as React from "react";
import { ChevronDown, ChevronRight, Loader2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AdminUnauthorized, startSeed } from "@/lib/api";
import type { SeedJob } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ACTIVE, SOURCE_LABELS, SummaryRow } from "@/components/admin-shared";

type SeedSource =
  | "famous"
  | "github_search"
  | "url_list"
  | "design_library";

/** Seeding settings section: source form + live queue (In progress) + run
 * history (Seed summary). Seeds queue FIFO on their own worker — two sources
 * never seed in parallel; verification runs on a separate worker at the same
 * time. */
export function SeedSection({
  jobs,
  expanded,
  onToggle,
  onSeeded,
  onLocked,
}: {
  jobs: SeedJob[];
  expanded: Set<string>;
  onToggle: (key: string) => void;
  onSeeded: () => void;
  onLocked: (msg?: string) => void;
}) {
  const [source, setSource] = React.useState<SeedSource>("famous");
  const [cap, setCap] = React.useState("30");
  const [query, setQuery] = React.useState("stars:>10000");
  const [urls, setUrls] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [tab, setTab] = React.useState<"run" | "summary">("run");

  const seedJobs = React.useMemo(() => jobs.filter((j) => j.kind === "seed"), [jobs]);
  const activeJobs = React.useMemo(
    () => seedJobs.filter((j) => ACTIVE.has(j.status)),
    [seedJobs],
  );
  const finishedJobs = React.useMemo(
    () => seedJobs.filter((j) => !ACTIVE.has(j.status)),
    [seedJobs],
  );

  const run = async () => {
    const capNum = Number(cap);
    if (!Number.isInteger(capNum) || capNum < 1 || capNum > 500) {
      toast.error("Cap must be a whole number between 1 and 500");
      return;
    }
    const params: Record<string, unknown> = { cap: capNum };
    if (source === "github_search") params.query = query.trim();
    if (source === "url_list") params.urls = urls;
    setBusy(true);
    try {
      await startSeed(source, params);
      toast.info(
        activeJobs.length > 0 ? "Queued — will seed after the current run" : "Seed started",
        { description: SOURCE_LABELS[source] ?? source },
      );
      onSeeded(); // refresh jobs list immediately so the new job shows up
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
        toast.error("Session expired — the drawer locked itself");
      } else {
        toast.error("Couldn't start the run", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Tabs value={tab} onValueChange={(v) => setTab(v as "run" | "summary")}>
      <TabsList className="grid w-full grid-cols-2 gap-1">
        <TabsTrigger value="run">Run</TabsTrigger>
        <TabsTrigger value="summary">Seed summary</TabsTrigger>
      </TabsList>

      <TabsContent value="run" className="space-y-3 pt-3">
        <Tabs value={source} onValueChange={(v) => setSource(v as SeedSource)}>
          <TabsList className="grid w-full grid-cols-4 gap-1">
            <TabsTrigger value="famous">Famous list</TabsTrigger>
            <TabsTrigger value="github_search">GitHub search</TabsTrigger>
            <TabsTrigger value="url_list">URL list</TabsTrigger>
            <TabsTrigger value="design_library">Design library</TabsTrigger>
          </TabsList>

          <TabsContent value="famous" className="space-y-2 pt-2">
            <p className="text-xs text-muted-foreground">
              Seeds from the bundled list of ~65 well-known startups
              (backend/data/seed_famous.json). Re-runs skip the LLM for entries already in the
              database.
            </p>
          </TabsContent>
          <TabsContent value="github_search" className="space-y-2 pt-2">
            <Label htmlFor="gh-q">GitHub search query</Label>
            <Input
              id="gh-q"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="stars:>10000"
            />
            <p className="text-xs text-muted-foreground">
              Hottest repos matching the query, sorted by stars. Examples:{" "}
              <code>stars:&gt;50000</code>, <code>topic:dev-tools stars:&gt;1000</code>.
            </p>
          </TabsContent>
          <TabsContent value="url_list" className="space-y-2 pt-2">
            <Label htmlFor="urls">URLs — one per line (websites or GitHub repos)</Label>
            <Textarea
              id="urls"
              rows={5}
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder={"https://example.com\nhttps://github.com/owner/repo"}
            />
          </TabsContent>
          <TabsContent value="design_library" className="space-y-2 pt-2">
            <p className="text-xs text-muted-foreground">
              Seeds 201 curated product sites from the design-scope reference library
              (backend/data/seed_design_library.json) — real homepages captured with
              design fingerprints. Website-only; re-runs skip the LLM for entries
              already in the database.
            </p>
          </TabsContent>
        </Tabs>

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="cap">Cap (per run)</Label>
            <Input
              id="cap"
              type="number"
              min={1}
              max={500}
              value={cap}
              onChange={(e) => setCap(e.target.value)}
              className="w-28"
            />
          </div>
          <Button onClick={run} disabled={busy} className="ml-auto">
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            {activeJobs.length > 0 ? "Queue seed" : "Run seed"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          1–500 · pull 30+ in testing
          {activeJobs.length > 0 &&
            ` · ${activeJobs.length} seed run${activeJobs.length > 1 ? "s" : ""} active — new seeds queue behind them`}
        </p>

        {/* Live queue — what's running now, what's waiting, and why */}
        {activeJobs.length > 0 && (
          <section className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              In progress
            </h3>
            {activeJobs.map((job) => {
              const pct = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
              return (
                <div key={job.id} className="space-y-2 rounded-lg bg-muted/40 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-x-2 text-xs">
                    <span className="flex items-center gap-1.5 font-medium">
                      {SOURCE_LABELS[job.source] ?? job.source}
                      {job.status === "queued" && (
                        <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">
                          queued #{job.queue_position ?? "?"}
                        </span>
                      )}
                    </span>
                    <span className="text-muted-foreground">
                      {job.done}/{job.total}
                      {job.total > 0 && ` · ${pct}%`} ·{" "}
                      <span className="text-success">{job.ok} ok</span>
                      {job.skipped > 0 && (
                        <span className="text-muted-foreground"> · {job.skipped} exist</span>
                      )}
                      {job.failed > 0 && (
                        <span className="text-destructive"> · {job.failed} failed</span>
                      )}
                    </span>
                  </div>
                  <Progress value={pct} className="h-1.5" />
                  {job.status === "running" ? (
                    <p className="truncate text-[11px] text-muted-foreground">
                      {job.current ? `Fetching ${job.current}…` : "Preparing…"}
                    </p>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">
                      Waiting for the current seed to finish — seeds never run in parallel
                      (verification can run alongside).
                    </p>
                  )}
                  {job.failed > 0 && (
                    <div className="space-y-1">
                      <button
                        type="button"
                        onClick={() => onToggle(`err:${job.id}`)}
                        className="flex items-center gap-1 text-xs font-medium text-destructive"
                      >
                        {expanded.has(`err:${job.id}`) ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                        <TriangleAlert className="h-3 w-3" />
                        {job.failed} failed — show details
                      </button>
                      {expanded.has(`err:${job.id}`) && (
                        <ul className="max-h-32 space-y-1 overflow-y-auto rounded bg-background/60 p-2 text-[11px] text-muted-foreground">
                          {job.errors.map((err, i) => (
                            <li key={i} className="break-words font-mono text-[10px]">
                              {err}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        )}
      </TabsContent>

      {/* Seed summary — persisted run history (survives backend restarts) */}
      <TabsContent value="summary" className="space-y-2 pt-3">
        {finishedJobs.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No seed runs yet — start one on the Run tab.
          </p>
        ) : (
          finishedJobs.map((job) => (
            <div key={job.id} className="space-y-1.5 rounded-lg bg-muted/40 p-3">
              <div className="flex flex-wrap items-center justify-between gap-x-2 text-xs">
                <span className="font-medium">{SOURCE_LABELS[job.source] ?? job.source}</span>
                <span
                  className={cn(
                    "text-muted-foreground",
                    job.status === "failed" && "text-destructive",
                  )}
                >
                  {job.status === "failed"
                    ? "failed"
                    : job.failed > 0
                      ? "done with failures"
                      : "done"}
                </span>
              </div>
              <SummaryRow
                label="Fetched"
                count={job.ok}
                items={job.ok_urls}
                open={expanded.has(`ok:${job.id}`)}
                onToggle={() => onToggle(`ok:${job.id}`)}
                tone="default"
              />
              <SummaryRow
                label="All exist"
                count={job.skipped}
                items={job.skipped_urls}
                open={expanded.has(`skip:${job.id}`)}
                onToggle={() => onToggle(`skip:${job.id}`)}
                tone="muted"
              />
              <SummaryRow
                label="Failed"
                count={job.failed}
                items={job.errors}
                open={expanded.has(`fail:${job.id}`)}
                onToggle={() => onToggle(`fail:${job.id}`)}
                tone="destructive"
              />
            </div>
          ))
        )}
      </TabsContent>
    </Tabs>
  );
}
