"use client";

import * as React from "react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

interface TickerItem {
  name: string;
  category: string;
  vintage: string;
  status: "verified" | "alive" | "checked";
}

const DEFAULT_TICKER_ITEMS: TickerItem[] = [
  { name: "Brex", category: "Finance", vintage: "2017", status: "verified" },
  { name: "Aalto", category: "Real Estate", vintage: "2021", status: "verified" },
  { name: "Airwallex", category: "FinTech", vintage: "2015", status: "verified" },
  { name: "Adyen", category: "Payments", vintage: "2006", status: "verified" },
  { name: "Chainalysis", category: "Blockchain", vintage: "2014", status: "verified" },
  { name: "Alpha Vantage", category: "Market Data", vintage: "2017", status: "verified" },
  { name: "Bitwise", category: "Asset Management", vintage: "2017", status: "verified" },
  { name: "Brightside", category: "FinTech", vintage: "2018", status: "verified" },
  { name: "Carta", category: "Equity Management", vintage: "2012", status: "verified" },
  { name: "Ajaib", category: "Investing", vintage: "2018", status: "verified" },
];

export function ArchivalTicker({
  items = DEFAULT_TICKER_ITEMS,
  className,
  onSelectItem,
}: {
  items?: TickerItem[];
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
              <span className="text-[10px] text-muted-foreground/60">/</span>
              <span className="text-muted-foreground/80">{item.category}</span>
              <span className="text-[10px] text-muted-foreground/60">·</span>
              <span className="text-[10px] tracking-wider text-muted-foreground/60">
                EST. {item.vintage}
              </span>
              <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-1.5 py-0.2 text-[9px] font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                VERIFIED
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
