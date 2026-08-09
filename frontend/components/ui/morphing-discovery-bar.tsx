"use client";

import React, { useRef } from "react";
import { motion, LayoutGroup, useReducedMotion } from "motion/react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

/* ---------- Types ---------- */
export interface DiscoveryCategory {
  id: string;
  label: string;
  icon: React.ReactNode;
  count?: number;
}

export interface MorphingDiscoveryBarProps {
  categories: DiscoveryCategory[];
  /** Active category id — null means "All". */
  value: string | null;
  onCategoryChange: (id: string | null) => void;
  query: string;
  onQueryChange: (q: string) => void;
  placeholder?: string;
  totalCount?: number;
  className?: string;
}

/* ---------- Motion ---------- */
const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Discovery bar — always-visible search input + a scrollable category chip
 * row with a shared-layout sliding active pill. Adapted from Watermelon UI
 * (MIT): the collapse-to-icon morph was removed so the search is a real,
 * discoverable input (user feedback); chips scroll (thin visible scrollbar +
 * wheel + drag) instead of clipping.
 */
export const MorphingDiscoveryBar: React.FC<MorphingDiscoveryBarProps> = ({
  categories,
  value,
  onCategoryChange,
  query,
  onQueryChange,
  placeholder = "Search the archive…",
  totalCount,
  className = "",
}) => {
  const reduce = useReducedMotion();
  const morph = reduce
    ? { type: "tween" as const, duration: 0 }
    : { type: "tween" as const, ease: EASE, duration: 0.35 };
  const chipsRef = useRef<HTMLDivElement>(null);

  const chips = [{ id: "__all", label: "All", count: totalCount, icon: null }, ...categories];

  // Wheel → horizontal scroll (trackpad/desktop), drag → scroll.
  const onChipsWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      el.scrollLeft += e.deltaY;
    }
  };

  return (
    <div className={cn("flex w-full flex-col items-center", className)}>
      <LayoutGroup>
        <motion.div
          layout
          transition={morph}
          className="glass flex w-full max-w-3xl items-center gap-1 rounded-full p-1.5"
        >
          {/* Search input — always visible */}
          <motion.div
            layout
            transition={morph}
            className="flex h-11 w-44 shrink-0 items-center gap-2 rounded-full bg-background/80 px-4 transition-shadow focus-within:ring-2 focus-within:ring-ring/50 sm:w-64"
          >
            <Search size={16} strokeWidth={2.5} className="shrink-0 text-muted-foreground" />
            <input
              aria-label="Search startups"
              placeholder={placeholder}
              className="h-full w-full bg-transparent font-mono text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
            />
          </motion.div>

          {/* Categories — scrollable row */}
          <motion.div
            ref={chipsRef}
            layout
            transition={morph}
            onWheel={onChipsWheel}
            className="chip-scroll flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto py-0.5"
          >
            {chips.map((cat) => {
              const active = (cat.id === "__all" ? null : cat.id) === value;
              return (
                <motion.button
                  key={cat.id}
                  type="button"
                  layout
                  onClick={() => onCategoryChange(cat.id === "__all" ? null : cat.id)}
                  aria-pressed={active}
                  className={cn(
                    "relative z-0 flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition-colors sm:px-3.5",
                    active ? "text-primary-foreground" : "text-foreground hover:bg-accent/60",
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="discovery-pill-bg"
                      className="absolute inset-0 z-[-1] rounded-full bg-primary shadow-sm"
                      transition={morph}
                    />
                  )}
                  {cat.icon && <span className="opacity-80">{cat.icon}</span>}
                  <span>{cat.label}</span>
                  {typeof cat.count === "number" && (
                    <span
                      className={cn(
                        "text-[10px] tabular-nums",
                        active ? "text-primary-foreground/70" : "text-muted-foreground",
                      )}
                    >
                      {cat.count}
                    </span>
                  )}
                </motion.button>
              );
            })}
          </motion.div>
        </motion.div>
      </LayoutGroup>
    </div>
  );
};
