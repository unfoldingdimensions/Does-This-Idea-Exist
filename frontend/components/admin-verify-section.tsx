"use client";

import * as React from "react";
import { CheckCheck, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AdminUnauthorized,
  approveSuggested,
  fetchStats,
  fetchSuggested,
} from "@/lib/api";
import type { Stats, SuggestedStartup } from "@/lib/types";
import { parseDbDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { BucketItem, SummaryRow } from "@/components/admin-shared";
import type { SeedJob } from "@/lib/types";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "never";
  const d = parseDbDate(iso);
  if (!d) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** "2026-08-11" → "Aug 11, 2026" (created_at is UTC "YYYY-MM-DD HH:MM:SS"). */
function dayLabel(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return day;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** Next UTC day as "YYYY-MM-DD" — the batch window is [day 00:00:00, nextDay 00:00:00). */
function nextUtcDay(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

/** Verification section — the human gate. The machine nominates alive-but-
 * unverified entries as "suggested verified"; the curator stamps them one-by-one
 * or in bulk (every approval behind a confirm dialog). The summary sub-tab
 * shows persisted verification history. */
export function VerificationSection({
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
  const [tab, setTab] = React.useState<"approve" | "summary">("approve");
  const [suggested, setSuggested] = React.useState<SuggestedStartup[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [approvingId, setApprovingId] = React.useState<number | null>(null);
  const [approvingAll, setApprovingAll] = React.useState(false);
  const [confirm, setConfirm] = React.useState<
    | { kind: "all" }
    | { kind: "batch"; day: string; count: number }
    | { kind: "one"; id: number; name: string }
    | null
  >(null);

  const refresh = React.useCallback(async () => {
    try {
      const [sug, st] = await Promise.all([fetchSuggested(), fetchStats()]);
      setSuggested(sug);
      setStats(st);
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      }
    }
  }, [onLocked]);

  React.useEffect(() => {
    // Initial load — deferred via timer (react-hooks v7 forbids synchronous
    // setState in effect bodies; the timeout callback is async and allowed).
    const t = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(t);
  }, [refresh]);

  const afterApprove = (n: number) => {
    setConfirm(null);
    setApprovingId(null);
    setApprovingAll(false);
    toast.success(`${n} filing${n === 1 ? "" : "s"} stamped`);
    onSeeded(); // refresh archive + jobs
    void refresh(); // refresh the queue
  };

  const approveOne = async (id: number) => {
    setApprovingId(id);
    try {
      const r = await approveSuggested([id]);
      afterApprove(r.approved);
    } catch (err) {
      setApprovingId(null);
      setConfirm(null);
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The stamp didn't take", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    }
  };

  const approveAll = async () => {
    setApprovingAll(true);
    try {
      const r = await approveSuggested(undefined, true);
      afterApprove(r.approved);
    } catch (err) {
      setApprovingAll(false);
      setConfirm(null);
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The stamp didn't take", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    }
  };

  /** Approve one created-day batch — the "approve this seed run" boundary:
   * every suggested row created that UTC day gets stamped in one action. */
  const approveBatch = async (day: string) => {
    setApprovingAll(true);
    try {
      const r = await approveSuggested(undefined, false, `${day} 00:00:00`, `${nextUtcDay(day)} 00:00:00`);
      afterApprove(r.approved);
    } catch (err) {
      setApprovingAll(false);
      setConfirm(null);
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("Couldn't stamp that batch", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    }
  };

  // Suggested rows grouped by created day (UTC) — one batch per seed run day.
  const groups = React.useMemo(() => {
    const byDay = new Map<string, SuggestedStartup[]>();
    for (const s of suggested) {
      const day = (s.created_at ?? "").slice(0, 10);
      if (!day) continue;
      const arr = byDay.get(day) ?? [];
      arr.push(s);
      byDay.set(day, arr);
    }
    return [...byDay.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [suggested]);

  const verifyJobs = React.useMemo(() => jobs.filter((j) => j.kind === "verify"), [jobs]);
  const lastVerified = stats?.last_checked ?? null;
  const verifiedCount = stats?.verified ?? 0;

  return (
    <>
      <Tabs value={tab} onValueChange={(v) => setTab(v as "approve" | "summary")}>
        <TabsList className="grid w-full grid-cols-2 gap-1">
          <TabsTrigger value="approve">Approve</TabsTrigger>
          <TabsTrigger value="summary">Verification summary</TabsTrigger>
        </TabsList>

        <TabsContent value="approve" className="space-y-3 pt-3">
          {/* Header: last complete verification date + verified count at last run */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
            <span className="text-muted-foreground">
              Last verification{" "}
              <span className="font-medium text-foreground">{fmtDate(lastVerified)}</span>
            </span>
            <span className="text-muted-foreground">
              <span className="font-medium text-success">{verifiedCount} verified</span> at
              last run
            </span>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              The automated check found these alive but no human has stamped them yet.
            </p>
            {suggested.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirm({ kind: "all" })}
                disabled={approvingAll}
              >
                {approvingAll ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCheck className="h-3.5 w-3.5" />
                )}
                Mark all
              </Button>
            )}
          </div>

          {suggested.length === 0 ? (
            <p className="rounded-lg bg-background/60 p-3 text-xs text-muted-foreground">
              Nothing to approve — the archive is fully verified or nothing&apos;s been checked
              yet.
            </p>
          ) : (
            <div className="max-h-72 space-y-3 overflow-y-auto pr-1">
              {groups.map(([day, items]) => (
                <div key={day} className="space-y-1">
                  <div className="flex items-center justify-between pt-0.5">
                    <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                      {dayLabel(day)} · {items.length}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 gap-1 px-2 text-[10px]"
                      onClick={() => setConfirm({ kind: "batch", day, count: items.length })}
                      disabled={approvingAll}
                    >
                      Approve batch
                    </Button>
                  </div>
                  <ul className="space-y-1">
                    {items.map((s) => (
                      <BucketItem
                        key={s.id}
                        name={s.name}
                        url={s.website_url ?? s.github_url ?? ""}
                        onApprove={() => setConfirm({ kind: "one", id: s.id, name: s.name })}
                        approving={approvingId === s.id}
                      />
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Verification summary — persisted history (survives backend restarts) */}
        <TabsContent value="summary" className="space-y-2 pt-3">
          {verifyJobs.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No verification runs yet — start one in Website Health Check.
            </p>
          ) : (
            verifyJobs.map((job) => (
              <div key={job.id} className="space-y-1.5 rounded-lg bg-muted/40 p-3">
                <div className="flex flex-wrap items-center justify-between gap-x-2 text-xs">
                  <span className="font-medium">
                    {fmtDate(
                      job.finished_at
                        ? new Date(job.finished_at * 1000).toISOString()
                        : null,
                    )}
                  </span>
                  <span
                    className={cn(
                      "text-muted-foreground",
                      job.status === "failed" && "text-destructive",
                    )}
                  >
                    {job.status === "failed"
                      ? "failed"
                      : `${job.done}/${job.total} checked · ${job.failed} failed`}
                  </span>
                </div>
                <SummaryRow
                  label="Already verified"
                  count={job.result?.already_verified.length ?? 0}
                  items={(job.result?.already_verified ?? []).map((b) => b.name)}
                  open={expanded.has(`av:${job.id}`)}
                  onToggle={() => onToggle(`av:${job.id}`)}
                  tone="default"
                />
                <SummaryRow
                  label="Suggested verified"
                  count={job.result?.suggested.length ?? 0}
                  items={(job.result?.suggested ?? []).map((b) => b.name)}
                  open={expanded.has(`sug:${job.id}`)}
                  onToggle={() => onToggle(`sug:${job.id}`)}
                  tone="muted"
                />
                <SummaryRow
                  label="Failed"
                  count={job.result?.failed_list.length ?? 0}
                  items={(job.result?.failed_list ?? []).map((b) => `${b.name} — ${b.reason}`)}
                  open={expanded.has(`vfail:${job.id}`)}
                  onToggle={() => onToggle(`vfail:${job.id}`)}
                  tone="destructive"
                />
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* Confirm dialog — every approval is behind this (user decision #2) */}
      <Dialog
        open={confirm !== null}
        onOpenChange={(v) => {
          // Block Escape/backdrop close while an approval POST is in flight —
          // otherwise the success toast fires into a vanished dialog.
          if (!v && !approvingAll && approvingId === null) setConfirm(null);
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {confirm?.kind === "all"
                ? `Approve all ${suggested.length} suggested?`
                : confirm?.kind === "batch"
                  ? `Approve ${confirm.count} from ${dayLabel(confirm.day)}?`
                  : `Mark ${confirm?.kind === "one" ? confirm.name : ""} as verified?`}
            </DialogTitle>
            <DialogDescription>
              {confirm?.kind === "all"
                ? "Every entry the automated check found alive gets the human-verified stamp. This is a human decision — you can still unverify any of them from the status pill."
                : confirm?.kind === "batch"
                  ? `Every suggested entry created on ${dayLabel(confirm.day)} gets the human-verified stamp — one action per seed batch. Reversible from the status pill.`
                  : "Confirm this startup actually exists — the verified badge is the human-gate stamp."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-end">
            <Button
              variant="ghost"
              onClick={() => setConfirm(null)}
              disabled={approvingAll || approvingId !== null}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!confirm) return;
                if (confirm.kind === "all") void approveAll();
                else if (confirm.kind === "batch") void approveBatch(confirm.day);
                else void approveOne(confirm.id);
              }}
              disabled={approvingAll || approvingId !== null}
            >
              {(approvingAll || approvingId !== null) && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              Confirm verified
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
