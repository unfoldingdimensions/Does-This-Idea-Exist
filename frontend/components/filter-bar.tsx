"use client";

import * as React from "react";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EASE } from "@/lib/motion";
import { CountUp } from "@/components/count-up";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SortKey } from "@/lib/search";
import { cn } from "@/lib/utils";

const SORT_LABELS: Record<SortKey, string> = {
  top: "Top (stars)",
  newest: "Newest added",
  verified: "Recently verified",
  name: "Name A–Z",
  founded: "Founded date",
};

// While a query is active the default sort is relevance (search.ts keeps Fuse
// ranking when sort==="top"), so the select must say so — "Top (stars)" would
// be a lie, and picking it would be a no-op. "Relevance" replaces it until the
// query clears.
const RELEVANCE_VALUE = "relevance";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "verified", label: "Verified" },
  { value: "unverified", label: "Unverified" },
  { value: "dead", label: "Dead" },
];

/** The active-facet dot — border+bg only, never ring/box-shadow (the select
    trigger already spends box-shadow on its focus ring). */
function ActiveDot({ active }: { active: boolean }) {
  if (!active) return null;
  return <span aria-hidden className="size-1 shrink-0 rounded-full bg-primary" />;
}

/** Per-facet clear-× — pointerdown-stopped so it never opens the select. */
function FacetClear({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <button
      type="button"
      aria-label={`Clear ${label}`}
      title={`Clear ${label}`}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onClear();
      }}
      className="flex size-4 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      <X className="h-2.5 w-2.5" />
    </button>
  );
}

export function FilterBar({
  sort,
  onSort,
  year,
  onYear,
  status,
  onStatus,
  years,
  count,
  onClear,
  showClear = false,
  searching = false,
}: {
  sort: SortKey;
  onSort: (k: SortKey) => void;
  year: string;
  onYear: (y: string) => void;
  status: string;
  onStatus: (s: string) => void;
  years: string[];
  count: number;
  onClear: () => void;
  showClear?: boolean;
  searching?: boolean;
}) {
  // While searching on the default sort, the select's value/options present
  // "Relevance"; choosing any other sort exits it (mapped back to "top").
  const relevanceActive = searching && sort === "top";
  const sortValue = relevanceActive ? RELEVANCE_VALUE : sort;
  const sortOptions: { value: string; label: string }[] = relevanceActive
    ? [
        { value: RELEVANCE_VALUE, label: "Relevance" },
        ...Object.entries(SORT_LABELS).map(([v, l]) => ({ value: v, label: l })),
      ]
    : Object.entries(SORT_LABELS).map(([v, l]) => ({ value: v, label: l }));

  return (
    <div className="flex flex-wrap items-center gap-2 pb-6">
      <span
        className="font-mono text-xs tabular-nums text-muted-foreground"
        aria-live="polite"
      >
        {/* Animated digits are aria-hidden; the live region gets the plain
            final number in sr-only (an animating CountUp would announce
            every frame). */}
        <span aria-hidden="true">
          <CountUp value={count} />{" "}
        </span>
        <span className="sr-only">{count}</span>
        {count === 1 ? "startup" : "startups"}
      </span>
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <Select value={year} onValueChange={onYear}>
          <SelectTrigger
            className={cn(
              "glass h-8 w-32 rounded-full text-xs",
              year !== "all" && "border-primary/50 bg-primary/10",
            )}
            aria-label="Filter by founded year"
          >
            <ActiveDot active={year !== "all"} />
            <SelectValue placeholder="Founded year" />
            {year !== "all" && <FacetClear label="founded year filter" onClear={() => onYear("all")} />}
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            <SelectItem value="all">All years</SelectItem>
            {years.map((y) => (
              <SelectItem key={y} value={y}>
                {y}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={onStatus}>
          <SelectTrigger
            className={cn(
              "glass h-8 w-32 rounded-full text-xs",
              status !== "all" && "border-primary/50 bg-primary/10",
            )}
            aria-label="Filter by status"
          >
            <ActiveDot active={status !== "all"} />
            <SelectValue placeholder="Status" />
            {status !== "all" && <FacetClear label="status filter" onClear={() => onStatus("all")} />}
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sortValue} onValueChange={(v) => onSort(v === RELEVANCE_VALUE ? "top" : (v as SortKey))}>
          <SelectTrigger
            className={cn(
              "glass h-8 w-36 rounded-full text-xs",
              !relevanceActive && sort !== "top" && "border-primary/50 bg-primary/10",
            )}
            aria-label="Sort startups"
          >
            <ActiveDot active={!relevanceActive && sort !== "top"} />
            <SelectValue placeholder="Sort" />
            {!relevanceActive && sort !== "top" && <FacetClear label="sort" onClear={() => onSort("top")} />}
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            {sortOptions.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <AnimatePresence>
          {showClear && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ type: "tween", ease: EASE, duration: 0.18 }}
            >
              <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={onClear}>
                <X className="h-3 w-3" /> Clear all
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
