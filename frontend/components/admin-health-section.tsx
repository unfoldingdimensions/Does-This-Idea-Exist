"use client";

import * as React from "react";
import { CheckCircle2, Loader2, Play, RefreshCw, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AdminUnauthorized, currentVerification, markVerified, runVerification, verificationStatus } from "@/lib/api";
import type { VerifyJob } from "@/lib/types";
import { BucketItem, SummaryRow } from "@/components/admin-shared";
import { cn } from "@/lib/utils";

/** Website Health Check section — the automated liveness pass. Same progress
 * bar + breakdown as before, plus three expandable output buckets
 * (Already verified / Suggested verified / Failed) with open-link and
 * Mark-verified actions on Suggested + Failed rows. */
export function HealthCheckSection({
  expanded,
  onToggle,
  onSeeded,
  onLocked,
}: {
  expanded: Set<string>;
  onToggle: (key: string) => void;
  onSeeded: () => void;
  onLocked: (msg?: string) => void;
}) {
  const [job, setJob] = React.useState<VerifyJob | null>(null);
  const [starting, setStarting] = React.useState(false);
  const [confirm, setConfirm] = React.useState<{ id: number; name: string } | null>(null);
  const [approving, setApproving] = React.useState(false);

  const pct =
    job && job.total > 0 ? Math.min(100, Math.round((job.done / job.total) * 100)) : 0;
  const b = job?.breakdown ?? { verified: 0, unverified: 0, dead: 0 };
  const result = job?.result;

  const pollRef = React.useRef<((jobId: string) => void) | null>(null);
  // The poll chain is recursive setTimeouts against THIS component. The admin
  // panel unmounts the section whenever its accordion closes — without the
  // alive guard + timer cleanup the chain kept firing every 2s at a dead
  // component, and a remount stacked a second chain on top.
  const aliveRef = React.useRef(true);
  const timerRef = React.useRef<number | null>(null);
  React.useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, []);

  const poll = React.useCallback(
    async (jobId: string) => {
      // Every failure path has to be caught here. This runs fire-and-forget
      // from a setTimeout, so an unhandled rejection (backend restart, job
      // evicted → 404) would silently end polling and leave `starting` stuck
      // true — the button disabled forever with nothing shown to the user.
      let s;
      try {
        s = await verificationStatus(jobId);
      } catch (err) {
        if (!aliveRef.current) return;
        setStarting(false);
        if (err instanceof AdminUnauthorized) {
          onLocked("Admin session expired — re-enter your token");
        } else {
          toast.error(err instanceof Error ? err.message : "Lost track of the verification job");
        }
        return;
      }
      if (!aliveRef.current) return;
      setJob(s);
      if (s.status === "queued" || s.status === "running") {
        timerRef.current = window.setTimeout(() => pollRef.current?.(jobId), 2000);
      } else {
        setStarting(false);
        if (!aliveRef.current) return;
        onSeeded();
        if (s.status === "failed") {
          toast.error("The health pass stumbled", {
            description: s.errors[0] ?? "See the panel for details.",
          });
        } else {
          toast.success(`Verified ${s.result?.ok ?? 0}/${s.total} · ${s.result?.flagged ?? 0} flagged`, {
            description:
              (s.result?.dead_flipped.length ?? 0) > 0
                ? `Filed dead: ${s.result?.dead_flipped.join(", ")}`
                : "No dead entries flipped.",
          });
        }
      }
    },
    [onSeeded, onLocked],
  );
  React.useEffect(() => {
    pollRef.current = poll;
  }, [poll]);

  // Re-attach to an in-flight pass when the section mounts (cron-triggered or
  // started in an earlier session — the worker keeps going server-side).
  // Once per mount: re-running on every `poll` identity change attached a
  // SECOND live chain while the first kept polling.
  React.useEffect(() => {
    let cancelled = false;
    void currentVerification()
      .then((active) => {
        if (cancelled || !active) return;
        setJob(active);
        void pollRef.current?.(active.id);
      })
      // Re-attach is best-effort: nothing in flight to show is the normal case,
      // and a locked/expired session is handled when the panel next acts.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const start = async () => {
    if (starting || job?.status === "running" || job?.status === "queued") return;
    setStarting(true);
    // Don't clear the previous run's results until the POST actually succeeds —
    // a 409/403/network failure was otherwise blanking a view the user still
    // wanted, leaving only a toast behind.
    try {
      const { job_id } = await runVerification();
      setJob(null);
      void poll(job_id);
    } catch (err) {
      setStarting(false);
      toast.error("Couldn't start the pass", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const approveOne = async () => {
    if (!confirm) return;
    setApproving(true);
    try {
      // A Failed row violates the archive-approve guard by construction
      // (it either carries strikes or is human-stamped), so the bulk
      // approve endpoint stored nothing here and the row just vanished
      // from local state — a no-op dressed as success. The single-row
      // verify endpoint is the correct call: it resets the strike
      // counter and revives a dead row (POST /api/startups/{id}/verify).
      await markVerified(confirm.id);
      toast.success("Verified — strikes reset");
      onSeeded();
      // Drop the stamped row from the local buckets immediately — the job's
      // result is a terminal snapshot the server won't update, and leaving
      // the row there invited a re-approve that did nothing.
      const stampedId = confirm.id;
      setJob((j) =>
        j && j.result
          ? {
              ...j,
              result: {
                ...j.result,
                suggested: j.result.suggested.filter((x) => x.id !== stampedId),
                failed_list: j.result.failed_list.filter((x) => x.id !== stampedId),
              },
            }
          : j,
      );
      setConfirm(null);
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The stamp didn't take", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Walks every website + GitHub repo and files dead links after 3 consecutive
          failures. Never touches the verified stamp — that&apos;s the Verification section&apos;s
          job. Runs alongside seeding (separate worker).
        </p>
        <Button onClick={start} disabled={starting || job?.status === "running" || job?.status === "queued"} size="sm" className="shrink-0">
          {starting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : job?.status === "running" || job?.status === "queued" ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {job?.status === "running" || job?.status === "queued" ? "Running…" : "Run verification"}
        </Button>
      </div>

      {job && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between text-xs">
              <span className="font-medium text-foreground">
                {job.done}/{job.total} checked
              </span>
              <span className="font-mono tabular-nums text-muted-foreground">{pct}%</span>
            </div>
            <Progress value={pct} className="h-1.5" />
          </div>

          {/* Breakdown — the archive composition at check time */}
          <dl className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-background/60 p-2">
              <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Verified</dt>
              <dd className="font-mono text-lg font-bold tabular-nums text-success">{b.verified}</dd>
            </div>
            <div className="rounded-lg bg-background/60 p-2">
              <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Unverified</dt>
              <dd className="font-mono text-lg font-bold tabular-nums text-muted-foreground">{b.unverified}</dd>
            </div>
            <div className="rounded-lg bg-background/60 p-2">
              <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Dead</dt>
              <dd className="font-mono text-lg font-bold tabular-nums text-destructive">{b.dead}</dd>
            </div>
          </dl>

          {job.status === "running" || job.status === "queued" ? (
            <>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                {job.status === "queued" ? (
                  <>Queued #{job.queue_position ?? "?"} — waiting for the current run to finish…</>
                ) : job.current ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking {job.current}…
                  </>
                ) : (
                  "Preparing…"
                )}
              </p>
              {job.failed > 0 && (
                <div className="space-y-1">
                  <button
                    type="button"
                    onClick={() => onToggle(`herr:${job.id}`)}
                    className="flex items-center gap-1 text-xs font-medium text-destructive"
                  >
                    <TriangleAlert className="h-3 w-3" />
                    {job.failed} failed — show details
                  </button>
                  {expanded.has(`herr:${job.id}`) && (
                    <ul className="max-h-32 space-y-1 overflow-y-auto rounded bg-background/60 p-2 text-[11px] text-muted-foreground">
                      {job.errors.map((err, i) => (
                        <li key={i} className="break-words font-mono text-[10px]">{err}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          ) : (
            /* Terminal — three expandable output buckets */
            <div className="space-y-1.5">
              <SummaryRow
                label="Already verified"
                count={result?.already_verified.length ?? 0}
                items={(result?.already_verified ?? []).map((x) => x.name)}
                open={expanded.has(`halready:${job.id}`)}
                onToggle={() => onToggle(`halready:${job.id}`)}
                tone="default"
              />
              <div className="rounded-lg bg-background/60">
                <button
                  type="button"
                  onClick={() => onToggle(`hsuggested:${job.id}`)}
                  disabled={(result?.suggested.length ?? 0) === 0}
                  className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-[11px] font-medium text-foreground transition-colors hover:bg-accent/50 disabled:cursor-default"
                >
                  {(result?.suggested.length ?? 0) > 0 ? (
                    <CheckCircle2
                      className={cn(
                        "h-3 w-3 shrink-0",
                        expanded.has(`hsuggested:${job.id}`) && "text-success",
                      )}
                    />
                  ) : (
                    <span className="w-3 shrink-0" />
                  )}
                  Suggested verified <span className="tabular-nums">{result?.suggested.length ?? 0}</span>
                </button>
                {expanded.has(`hsuggested:${job.id}`) && (result?.suggested.length ?? 0) > 0 && (
                  <ul className="max-h-40 space-y-1 overflow-y-auto px-2 pb-2">
                    {result?.suggested.map((x) => (
                      <BucketItem
                        key={x.id}
                        name={x.name}
                        url={x.url}
                        onApprove={() => setConfirm({ id: x.id, name: x.name })}
                      />
                    ))}
                  </ul>
                )}
              </div>
              <div className="rounded-lg bg-background/60">
                <button
                  type="button"
                  onClick={() => onToggle(`hfailed:${job.id}`)}
                  disabled={(result?.failed_list.length ?? 0) === 0}
                  className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-[11px] font-medium text-destructive transition-colors hover:bg-accent/50 disabled:cursor-default"
                >
                  {(result?.failed_list.length ?? 0) > 0 ? (
                    <TriangleAlert
                      className={cn(
                        "h-3 w-3 shrink-0",
                        expanded.has(`hfailed:${job.id}`) && "text-destructive",
                      )}
                    />
                  ) : (
                    <span className="w-3 shrink-0" />
                  )}
                  Failed <span className="tabular-nums">{result?.failed_list.length ?? 0}</span>
                </button>
                {expanded.has(`hfailed:${job.id}`) && (result?.failed_list.length ?? 0) > 0 && (
                  <ul className="max-h-40 space-y-1 overflow-y-auto px-2 pb-2">
                    {result?.failed_list.map((x) => (
                      <BucketItem
                        key={x.id}
                        name={x.name}
                        url={x.url}
                        reason={x.reason}
                        onApprove={() => setConfirm({ id: x.id, name: x.name })}
                      />
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirm dialog — marking verified from the buckets is a human decision */}
      <Dialog
        open={confirm !== null}
        onOpenChange={(v) => {
          if (!v && !approving) setConfirm(null);
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Mark {confirm?.name ?? ""} as verified?</DialogTitle>
            <DialogDescription>
              This re-check failed — the entry gets a verified stamp, its strike counter is
              reset and a dead filing is revived. Reversible from the status pill.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-end">
            <Button variant="ghost" onClick={() => setConfirm(null)} disabled={approving}>
              Cancel
            </Button>
            <Button onClick={approveOne} disabled={approving}>
              {approving && <Loader2 className="h-4 w-4 animate-spin" />}
              Confirm verified
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
