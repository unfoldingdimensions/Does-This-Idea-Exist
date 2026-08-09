"use client";

import * as React from "react";
import { ChevronDown, ChevronRight, Loader2, Settings2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AdminUnauthorized,
  adminCheck,
  clearAdminToken,
  getAdminToken,
  seedStatus,
  setAdminToken,
  startSeed,
} from "@/lib/api";
import type { SeedJob } from "@/lib/types";

const SOURCE_LABELS: Record<string, string> = {
  famous: "Famous list",
  github_search: "GitHub search",
  url_list: "URL list",
  topstartups: "Top Startups",
};

type SeedSource = "famous" | "github_search" | "url_list" | "topstartups";

/** Owner-only seeder: token unlock → source tabs → live job progress. Failures are loud. */
export function AdminPanel({ onSeeded }: { onSeeded: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [token, setToken] = React.useState<string | null>(() => getAdminToken());
  const [tokenInput, setTokenInput] = React.useState("");
  const [unlocking, setUnlocking] = React.useState(false);
  const [unlockMsg, setUnlockMsg] = React.useState("");

  const [source, setSource] = React.useState<SeedSource>("famous");
  const [cap, setCap] = React.useState("30");
  const [query, setQuery] = React.useState("stars:>10000");
  const [urls, setUrls] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [job, setJob] = React.useState<SeedJob | null>(null);
  const [showErrors, setShowErrors] = React.useState(false);

  const handleLocked = (msg?: string) => {
    clearAdminToken();
    setToken(null);
    setJob(null);
    if (msg) setUnlockMsg(msg);
  };

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim() || unlocking) return;
    setUnlocking(true);
    setUnlockMsg("");
    try {
      await adminCheck(tokenInput.trim());
      setAdminToken(tokenInput.trim());
      setToken(tokenInput.trim());
      setTokenInput("");
    } catch (err) {
      setUnlockMsg(err instanceof Error ? err.message : "Unlock failed");
    } finally {
      setUnlocking(false);
    }
  };

  const poll = async (jobId: string) => {
    try {
      const s = await seedStatus(jobId);
      setJob(s);
      if (s.status === "queued" || s.status === "running") {
        window.setTimeout(() => {
          void poll(jobId);
        }, 1500);
      } else {
        setBusy(false);
        onSeeded();
        if (s.status === "failed" || s.failed > 0) {
          toast.error(`Seed finished — ${s.done} done · ${s.failed} failed`, {
            description: s.errors[0] ?? "See the error list in the panel.",
          });
        } else {
          toast.success(`Seed complete — ${s.ok} added/updated`);
        }
      }
    } catch (err) {
      setBusy(false);
      if (err instanceof AdminUnauthorized) {
        handleLocked("Admin session expired — re-enter your token");
        toast.error("Admin session expired");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to read seed status");
      }
    }
  };

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
    setJob(null);
    setShowErrors(false);
    try {
      const { job_id } = await startSeed(source, params);
      void poll(job_id);
    } catch (err) {
      setBusy(false);
      if (err instanceof AdminUnauthorized) {
        handleLocked("Admin session expired — re-enter your token");
        toast.error("Admin session expired");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to start seed");
      }
    }
  };

  const progress = job && job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) setJob(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Admin panel" title="Admin — seeder" className="h-9 w-9">
          <Settings2 className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Admin — Seeder</DialogTitle>
          <DialogDescription>
            Batch-fetch startups from GitHub, the famous list, or pasted URLs. New entries start
            unverified — review them before marking verified.
          </DialogDescription>
        </DialogHeader>

        {!token ? (
          <form onSubmit={handleUnlock} className="space-y-3 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="admin-token">Admin token</Label>
              <Input
                id="admin-token"
                type="password"
                placeholder="Your owner token"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                disabled={unlocking}
                autoFocus
              />
            </div>
            {unlockMsg && <p className="text-xs text-destructive">{unlockMsg}</p>}
            <Button type="submit" disabled={unlocking || !tokenInput.trim()}>
              {unlocking && <Loader2 className="h-4 w-4 animate-spin" />}
              Unlock
            </Button>
          </form>
        ) : (
          <div className="space-y-4 pt-2">
            <Tabs
              value={source}
              onValueChange={(v) => setSource(v as SeedSource)}
            >
              <TabsList className="grid w-full grid-cols-4 gap-1">
                <TabsTrigger value="famous">Famous list</TabsTrigger>
                <TabsTrigger value="github_search">GitHub search</TabsTrigger>
                <TabsTrigger value="url_list">URL list</TabsTrigger>
                <TabsTrigger value="topstartups">Top Startups</TabsTrigger>
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
              <TabsContent value="topstartups" className="space-y-2 pt-2">
                <p className="text-xs text-muted-foreground">
                  Scrapes topstartups.io (1,259 funded startups, ~20 per page) — company
                  name + website per card, utm params stripped. Use a cap below ~40 per run
                  to keep each batch quick.
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
                Run seed
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">1–500 · pull 30+ in testing</p>

            {job && (
              <div className="space-y-2 rounded-lg bg-muted/40 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium">{SOURCE_LABELS[job.source] ?? job.source}</span>
                  <span className="text-muted-foreground">
                    {job.done}/{job.total} · <span className="text-success">{job.ok} ok</span>
                    {job.failed > 0 && <span className="text-destructive"> · {job.failed} failed</span>}
                  </span>
                </div>
                <Progress value={progress} className="h-1.5" />
                {job.status === "running" && job.current && (
                  <p className="truncate text-[11px] text-muted-foreground">Working on {job.current}</p>
                )}
                {job.failed > 0 && (
                  <div className="space-y-1">
                    <button
                      type="button"
                      onClick={() => setShowErrors((v) => !v)}
                      className="flex items-center gap-1 text-xs font-medium text-destructive"
                    >
                      {showErrors ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                      <TriangleAlert className="h-3 w-3" />
                      {job.failed} failed — show details
                    </button>
                    {showErrors && (
                      <ul className="max-h-32 space-y-1 overflow-y-auto rounded bg-background/60 p-2 text-[11px] text-muted-foreground">
                        {job.errors.map((err, i) => (
                          <li key={i} className="break-words">
                            {err}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
