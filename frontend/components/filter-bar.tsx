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
}) {
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
        <Select value={sort} onValueChange={(v) => onSort(v as SortKey)}>
          <SelectTrigger className="glass h-8 w-36 rounded-full text-xs" aria-label="Sort startups">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
              <SelectItem key={k} value={k}>
                {SORT_LABELS[k]}
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
