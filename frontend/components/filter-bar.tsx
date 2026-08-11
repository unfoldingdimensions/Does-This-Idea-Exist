"use client";

import * as React from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SortKey } from "@/lib/search";

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
        {count} {count === 1 ? "startup" : "startups"}
      </span>
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <Select value={year} onValueChange={onYear}>
          <SelectTrigger className="glass h-8 w-32 rounded-full text-xs" aria-label="Filter by founded year">
            <SelectValue placeholder="Founded year" />
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
          <SelectTrigger className="glass h-8 w-32 rounded-full text-xs" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
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
          <SelectTrigger className="glass h-8 w-36 rounded-full text-xs" aria-label="Sort startups">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            {sortOptions.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {showClear && (
          <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={onClear}>
            <X className="h-3 w-3" /> Clear all
          </Button>
        )}
      </div>
    </div>
  );
}
