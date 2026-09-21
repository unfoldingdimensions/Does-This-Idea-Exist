"use client";

import * as React from "react";
import { Loader2, RefreshCw, Waypoints } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AdminUnauthorized,
  importFunnelRun,
  type FunnelImportPlan,
} from "@/lib/api";

/**
 * Funnel import — the panel's window onto `POST /api/admin/funnel/import`.
 *
 * The liveness funnel (scripts/site_liveness_audit.py) decides; this applies
 * its decisions to the archive: the clean LIVE majority is machine-admitted,
 * exceptions queue for the human path, and dead rows stay the drop tool's
 * jurisdiction. Dry-run is always the first step — the operator sees exactly
 * what would be admitted/queued before anything is written, and the apply
 * action is a separate confirm.
 */
export function FunnelImportSection({
  onSeeded,
  onLocked,
}: {
  onSeeded: () => void;
  onLocked: (msg?: string) => void;
}) {
  const [run, setRun] = React.useState("");
  const [plan, setPlan] = React.useState<FunnelImportPlan | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [applying, setApplying] = React.useState(false);

  const call = async (dryRun: boolean) => {
    setBusy(true);
    try {
      const p = await importFunnelRun(run.trim(), dryRun);
      setPlan(p);
      if (dryRun) {
        toast.success(`Dry-run: ${p.admit_eligible} admit-eligible of ${p.total_rows} rows`);
      } else {
        toast.success(`${p.admitted.length} rows machine-admitted`);
        onSeeded();
      }
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("Funnel import failed", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setBusy(false);
      setApplying(false);
    }
  };

  return (
    <div className="space-y-3 pt-2">
      <p className="text-xs text-muted-foreground">
        Apply a completed liveness-funnel run (a run directory the audit tool
        wrote, relative to the backend root — e.g.{" "}
        <code className="rounded bg-muted/60 px-1 font-mono text-[10px]">
          liveness-out/liveness-2026-09-19-0013
        </code>
        ). Clean LIVE rows are machine-admitted; walled/unknown/non-company rows
        queue in Verification; dead rows stay with the drop tool. Dry-run first
        — nothing is written until you apply.
      </p>

      <div className="flex items-end gap-2">
        <div className="min-w-0 flex-1 space-y-1.5">
          <Label htmlFor="funnel-run-path">Run directory</Label>
          <Input
            id="funnel-run-path"
            placeholder="liveness-out/liveness-…"
            value={run}
            onChange={(e) => setRun(e.target.value)}
            disabled={busy}
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-9 gap-1.5"
          disabled={busy || !run.trim()}
          onClick={() => void call(true)}
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Dry-run
        </Button>
      </div>

      {plan && (
        <div className="space-y-2 rounded-lg bg-muted/40 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium">
              {plan.dry_run ? "Plan" : "Applied"} —{" "}
              <span className="font-mono text-[10px]">{plan.states_file}</span>
            </span>
            <span className="text-muted-foreground tabular-nums">
              {plan.total_rows} rows · {plan.already_admitted} already admitted ·{" "}
              {plan.unknown_ids.length} unknown
            </span>
          </div>
          <ul className="grid grid-cols-3 gap-2 text-center">
            <li className="rounded-md bg-background/60 p-2">
              <span className="block font-mono text-sm font-bold text-success tabular-nums">
                {plan.dry_run ? plan.admit_eligible : plan.admitted.length}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {plan.dry_run ? "admit-eligible" : "admitted"}
              </span>
            </li>
            <li className="rounded-md bg-background/60 p-2">
              <span className="block font-mono text-sm font-bold tabular-nums">
                {plan.queued.length}
              </span>
              <span className="text-[10px] text-muted-foreground">queued for you</span>
            </li>
            <li className="rounded-md bg-background/60 p-2">
              <span className="block font-mono text-sm font-bold text-muted-foreground tabular-nums">
                {plan.ignored.length}
              </span>
              <span className="text-[10px] text-muted-foreground">dead — drop&apos;s job</span>
            </li>
          </ul>
          {plan.queued.length > 0 && (
            <p className="text-[11px] text-muted-foreground">
              Queued:{" "}
              {plan.queued
                .slice(0, 6)
                .map((q) => `${q.name} (${(q.state || "—").toLowerCase()})`)
                .join(", ")}
              {plan.queued.length > 6 && ` … +${plan.queued.length - 6} more`}
            </p>
          )}
          {plan.dry_run && plan.admit_eligible > 0 && (
            <Button
              size="sm"
              className="gap-1.5"
              disabled={applying}
              onClick={() => {
                setApplying(true);
                void call(false);
              }}
            >
              {applying ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Waypoints className="h-3.5 w-3.5" />
              )}
              Apply — admit {plan.admit_eligible}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
