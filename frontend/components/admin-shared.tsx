"use client";

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ParkInfo, SeedJob, VerifyResult } from "@/lib/types";

export const SOURCE_LABELS: Record<string, string> = {
  famous: "Famous list",
  github_search: "GitHub search",
  url_list: "URL list",
  design_library: "Design library",
  verify: "Verification",
};

/**
 * The statuses a job is still *moving* in, for list membership: a parked job is
 * not finished — it is waiting on an operator — so it belongs in the in-progress
 * group rather than in history.
 */
export const ACTIVE = new Set(["queued", "running", "paused"]);

/**
 * Money, in the one form every surface uses. `null` is NOT $0.00 — it is "we do
 * not know", and a rate table that cannot price a model must never look free.
 */
export function money(value: number | null | undefined): string {
  return typeof value === "number" ? `$${value.toFixed(4)}` : "unknown";
}

/**
 * One honest line about why a job is parked (§7.4 spend brake). Shared so the
 * seed list and the parked banner can never disagree about the cause.
 *
 * A null spend means the ledger could not be read — that is "unknown", and it is
 * never rendered as $0.00. Costless wording when the job has unpriced calls: the
 * figure is a floor, not the bill.
 */
export function parkedReason(job: SeedJob): string {
  const park: ParkInfo | null =
    job.result && "stop_reason" in job.result ? (job.result as ParkInfo) : null;
  if (!park) return "stopped by the spend brake";
  if (park.stop_reason === "metering") {
    return "paused: the spend ledger could not be read, so the budget could not be checked";
  }
  const spent = money(park.spend_usd);
  const floor = park.cost_complete ? "" : " (a floor — some calls are unpriced)";
  return `paused at the budget: reached ${spent === "unknown" ? "an unknown amount" : spent}${floor} of $${park.cap_usd.toFixed(4)}`;
}

/**
 * The VERIFY result of a job, or null when this job does not have one (a seed
 * job's result is either null or a ParkInfo from the spend brake).
 *
 * One narrow instead of a cast at every call site: `checked` exists only on
 * VerifyResult, so the compiler proves the narrowing is real.
 */
export function verifyResult(job: SeedJob): VerifyResult | null {
  return job.result && "checked" in job.result ? job.result : null;
}

/** Expandable count row inside a run summary ("Fetched N", "All exist N", "Failed N"). */
export function SummaryRow({
  label,
  count,
  items,
  open,
  onToggle,
  tone,
}: {
  label: string;
  count: number;
  items: string[];
  open: boolean;
  onToggle: () => void;
  tone: "default" | "muted" | "destructive";
}) {
  return (
    <div className="rounded-lg bg-background/60">
      <button
        type="button"
        onClick={onToggle}
        disabled={count === 0}
        className={cn(
          "flex w-full items-center gap-1.5 px-2 py-1 text-left text-xs font-medium transition-colors",
          count === 0 ? "cursor-default" : "hover:bg-accent/50",
          tone === "destructive"
            ? "text-destructive"
            : tone === "muted"
              ? "text-muted-foreground"
              : "text-foreground",
        )}
      >
        {count > 0 ? (
          open ? (
            <ChevronDown className="h-3 w-3 shrink-0" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0" />
          )
        ) : (
          <span className="w-3 shrink-0" />
        )}
        <span>
          {label} <span className="tabular-nums">{count}</span>
        </span>
      </button>
      {open && count > 0 && (
        <ul className="max-h-32 space-y-0.5 overflow-y-auto px-2 pb-2 text-xs text-muted-foreground">
          {items.map((item, i) => (
            <li key={i} className="break-words font-mono text-[11px]">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Row-level actions for verify buckets: open the link + (optionally) mark verified. */
export function BucketItem({
  name,
  url,
  reason,
  onApprove,
  approving,
  approveLabel,
}: {
  name: string;
  url: string;
  reason?: string;
  onApprove?: () => void;
  approving?: boolean;
  /** Override the button copy — e.g. "Approve publish" for a founder request. */
  approveLabel?: string;
}) {
  return (
    <li className="flex items-center gap-1.5 rounded-md bg-background/60 px-2 py-1 text-xs">
      <span className="min-w-0 flex-1 truncate" title={reason ?? name}>
        {name}
        {reason && <span className="ml-1.5 text-[11px] text-muted-foreground">{reason}</span>}
      </span>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open ${name || "the filing"} in a new tab`}
          className="shrink-0 text-[11px] font-medium text-primary underline-offset-2 hover:underline"
        >
          open
        </a>
      )}
      {onApprove && (
        <button
          type="button"
          onClick={onApprove}
          disabled={approving}
          className="shrink-0 rounded-full bg-success/15 px-2 py-0.5 text-[11px] font-semibold text-success transition-colors hover:bg-success/25 disabled:opacity-50"
        >
          {approving ? "…" : approveLabel ?? "Mark verified"}
        </button>
      )}
    </li>
  );
}
