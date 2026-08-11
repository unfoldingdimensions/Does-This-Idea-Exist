"use client";

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export const SOURCE_LABELS: Record<string, string> = {
  famous: "Famous list",
  github_search: "GitHub search",
  url_list: "URL list",
  design_library: "Design library",
  verify: "Verification",
};

export const ACTIVE = new Set(["queued", "running"]);

/** Collapsible settings-section header (vertical accordion, one open at a time). */
export function SectionHeader({
  icon,
  title,
  open,
  onToggle,
  badge,
}: {
  icon: React.ReactNode;
  title: string;
  open: boolean;
  onToggle: () => void;
  badge?: string;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex w-full items-center gap-2 rounded-lg border bg-background/60 px-3 py-2.5 text-left text-sm font-semibold transition-colors",
        open ? "border-accent/60" : "hover:bg-accent/40",
      )}
    >
      {icon}
      <span className="flex-1">{title}</span>
      {badge && (
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
          {badge}
        </span>
      )}
      <ChevronDown
        className={cn(
          "h-4 w-4 text-muted-foreground transition-transform duration-200",
          !open && "-rotate-90",
        )}
      />
    </button>
  );
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
          "flex w-full items-center gap-1.5 px-2 py-1 text-left text-[11px] font-medium transition-colors",
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
        <ul className="max-h-32 space-y-0.5 overflow-y-auto px-2 pb-2 text-[11px] text-muted-foreground">
          {items.map((item, i) => (
            <li key={i} className="break-words font-mono text-[10px]">
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
}: {
  name: string;
  url: string;
  reason?: string;
  onApprove?: () => void;
  approving?: boolean;
}) {
  return (
    <li className="flex items-center gap-1.5 rounded-md bg-background/60 px-2 py-1 text-[11px]">
      <span className="min-w-0 flex-1 truncate" title={reason ?? name}>
        {name}
        {reason && <span className="ml-1.5 text-[10px] text-muted-foreground">{reason}</span>}
      </span>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-[10px] font-medium text-primary underline-offset-2 hover:underline"
        >
          open
        </a>
      )}
      {onApprove && (
        <button
          type="button"
          onClick={onApprove}
          disabled={approving}
          className="shrink-0 rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-semibold text-success transition-colors hover:bg-success/25 disabled:opacity-50"
        >
          {approving ? "…" : "Mark verified"}
        </button>
      )}
    </li>
  );
}
