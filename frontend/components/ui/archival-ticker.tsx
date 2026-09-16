"use client";

import * as React from "react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

/**
 * One filing on the marquee.
 *
 * `vintage` and `category` are OPTIONAL on purpose: the old default list
 * fabricated both (`"2021"` for a null founding date, `"FinTech"` for a null
 * category) and the ticker stamps a VERIFIED pill on every item regardless of
 * the record. Nothing here is invented now — a field the record does not have
 * is simply not rendered, and the pill comes from the row's real status.
 */
export interface TickerItem {
  name: string;
  category?: string;
  /** The year to print, already labelled by `foundedShort` where the source is
   * not a human confirmation. Absent when the record has no dated founding. */
  vintage?: string;
  /** `verified` = a human stamped it · `unverified` = filed, awaiting a human ·
   * `filed` = checked and gone (dead/pivoted). */
  status: "verified" | "unverified" | "filed";
}

const STATUS_META: Record<TickerItem["status"], { label: string; className: string }> = {
  verified: {
    label: "VERIFIED",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  unverified: {
    label: "UNVERIFIED",
    className: "bg-muted text-muted-foreground border-border/60",
  },
  filed: {
    label: "FILED",
    className: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

export function ArchivalTicker({
  items,
  className,
  onSelectItem,
}: {
  items: TickerItem[];
  className?: string;
  onSelectItem?: (name: string) => void;
}) {
  // Duplicate for infinite seamless marquee loop
  const displayItems = React.useMemo(() => [...items, ...items], [items]);

  return (
    <div
      className={cn(
        "relative flex w-full items-center overflow-hidden border-y border-border/40 bg-card/30 backdrop-blur-md py-1.5 text-xs select-none",
        className
      )}
      aria-label="Live archival filings ticker"
    >
      {/* Ticker Lead Tag */}
      <div className="relative z-10 flex shrink-0 items-center gap-2 border-r border-border/40 bg-background/80 px-3 py-0.5 text-[10px] font-mono tracking-widest uppercase text-muted-foreground backdrop-blur-sm">
        <span className="relative flex size-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
        </span>
        <span className="hidden sm:inline">LIVE FEED</span>
      </div>

      {/* Marquee Track */}
      <div className="flex w-full overflow-hidden">
        <div className="animate-marquee flex items-center gap-6 pl-4 font-mono text-[11px] text-muted-foreground">
          {displayItems.map((item, idx) => (
            <button
              key={`${item.name}-${idx}`}
              type="button"
              onClick={() => {
                sound.playTick();
                onSelectItem?.(item.name);
              }}
              className="group flex shrink-0 items-center gap-2 transition-colors hover:text-foreground focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary rounded px-1.5 py-0.5 cursor-pointer"
            >
              <span className="font-semibold text-foreground/90 group-hover:text-primary transition-colors">
                {item.name}
              </span>
              {item.category && (
                <>
                  <span className="text-[10px] text-muted-foreground/60">/</span>
                  <span className="text-muted-foreground/80">{item.category}</span>
                </>
              )}
              {item.vintage && (
                <>
                  <span className="text-[10px] text-muted-foreground/60">·</span>
                  <span className="text-[10px] tracking-wider text-muted-foreground/60">
                    EST. {item.vintage}
                  </span>
                </>
              )}
              <span
                className={cn(
                  "inline-flex items-center rounded-full border px-1.5 py-0.2 text-[9px] font-medium",
                  STATUS_META[item.status].className,
                )}
              >
                {STATUS_META[item.status].label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Gradient edge fades */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-background to-transparent z-10"
      />
    </div>
  );
}
