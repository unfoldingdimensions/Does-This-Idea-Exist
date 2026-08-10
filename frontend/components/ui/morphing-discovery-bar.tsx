"use client";

import React, { useRef } from "react";
import { motion, AnimatePresence, LayoutGroup, useReducedMotion } from "motion/react";
import { ChevronDown, Search, X } from "lucide-react";
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
 * Discovery bar — always-visible search input + a compact category bar:
 * "All" + the top 3 categories by count inline, then a "More" button that
 * opens a hover dropdown with every remaining category. The shared-layout
 * active pill morphs between the inline chips and the "More" button, so the
 * selection highlight slides wherever the active category lives. Adapted from
 * Watermelon UI (MIT): collapse-to-icon morph removed (search stays a real,
 * discoverable input); chips scroll on mobile only (thin visible scrollbar +
 * wheel + drag).
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

  // When the active chip changes (click or deep-linked URL), bring it into
  // view on the mobile scroll row so the morphing pill is never off-screen.
  const activeRef = useRef<HTMLButtonElement>(null);
  React.useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
    }
  }, [value]);

  /* --- "More" dropdown state (hover-open, click toggles for touch/keyboard) --- */
  const [moreOpen, setMoreOpen] = React.useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const moreTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const openMore = () => {
    if (moreTimer.current) clearTimeout(moreTimer.current);
    setMoreOpen(true);
  };
  const closeMore = () => {
    moreTimer.current = setTimeout(() => setMoreOpen(false), 150);
  };

  // Close on outside click (touch / click-away).
  React.useEffect(() => {
    if (!moreOpen) return;
    const onDocDown = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocDown);
    return () => document.removeEventListener("mousedown", onDocDown);
  }, [moreOpen]);

  // Cleanup timers on unmount.
  React.useEffect(() => {
    return () => {
      if (moreTimer.current) clearTimeout(moreTimer.current);
    };
  }, []);

  // Categories arrive sorted by count desc (page.tsx) — top 3 inline, rest in "More".
  const chips = [{ id: "__all", label: "All", count: totalCount, icon: null }, ...categories];
  const visibleChips = chips.slice(0, 4); // All + top 3
  const moreChips = chips.slice(4);
  const activeInMore = moreChips.some((c) => (c.id === "__all" ? null : c.id) === value);

  // Wheel → horizontal scroll (trackpad/desktop), drag → scroll.
  const onChipsWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      el.scrollLeft += e.deltaY;
    }
  };

  return (
    <div className={cn("relative z-30 flex w-full flex-col items-center", className)}>
      <LayoutGroup>
        <motion.div
          layout
          transition={morph}
          className="glass flex w-full max-w-3xl items-center gap-1 rounded-[1.75rem] p-1.5"
        >
          {/* Search input — always visible */}
          <motion.div
            layout
            transition={morph}
            className="relative flex h-11 w-44 shrink-0 items-center gap-2 rounded-full bg-background/80 px-4 transition-shadow sm:w-64"
          >
            {/* The ring target is a plain (non-motion) wrapper that owns the
                input: framer-motion's layout projection writes an inline
                transparent box-shadow on motion elements, which would clobber
                a ring on this pill. :focus-within on the wrapper matches when
                the input inside it is focused. */}
            <div className="search-focus-ring flex h-full w-full items-center gap-2 rounded-full">
              <Search size={16} strokeWidth={2.5} className="shrink-0 text-muted-foreground" />
              <input
                aria-label="Search startups"
                placeholder={placeholder}
                className={cn(
                  "h-full w-full bg-transparent font-mono text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground",
                  query && "pr-6",
                )}
                value={query}
                onChange={(e) => onQueryChange(e.target.value)}
              />
              {query && (
                <button
                  type="button"
                  aria-label="Clear search"
                  title="Clear search"
                  onClick={() => onQueryChange("")}
                  className="absolute right-2.5 flex size-5 items-center justify-center rounded-full bg-muted text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  <X size={12} strokeWidth={2.5} />
                </button>
              )}
            </div>
          </motion.div>

          {/* Category bar — All + top 3 inline, "More" opens the rest.
              Mobile keeps a horizontal scroll fallback for very narrow rows. */}
          <motion.div
            ref={chipsRef}
            layout
            transition={morph}
            onWheel={onChipsWheel}
            className="chip-scroll flex min-w-0 flex-1 flex-nowrap items-center gap-0.5 overflow-x-auto py-0.5"
          >
            {visibleChips.map((cat) => {
              const active = (cat.id === "__all" ? null : cat.id) === value;
              return (
                <motion.button
                  key={cat.id}
                  type="button"
                  layout
                  ref={active ? activeRef : undefined}
                  onClick={() => onCategoryChange(cat.id === "__all" ? null : cat.id)}
                  aria-pressed={active}
                  className={cn(
                    "relative z-0 flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition-colors sm:px-3.5",
                    active ? "text-primary-foreground" : "text-foreground hover:bg-accent/60",
                  )}
                >
                  <AnimatePresence initial={false}>
                    {active && (
                      <motion.span
                        layoutId="discovery-pill-bg"
                        className="absolute inset-0 z-[-1] rounded-full bg-primary shadow-sm"
                        transition={morph}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                      />
                    )}
                  </AnimatePresence>
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

          {/* More button — sits OUTSIDE the chip-scroll container so its
              dropdown is never clipped by the row's overflow-x. */}
          {moreChips.length > 0 && (
            <div
              ref={moreRef}
              className="relative shrink-0"
              onMouseEnter={openMore}
              onMouseLeave={closeMore}
            >
              <motion.button
                type="button"
                layout
                onClick={() => setMoreOpen((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={moreOpen}
                className={cn(
                  "relative z-0 flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition-colors sm:px-3.5",
                  activeInMore ? "text-primary-foreground" : "text-foreground hover:bg-accent/60",
                )}
              >
                <AnimatePresence initial={false}>
                  {activeInMore && (
                    <motion.span
                      className="absolute inset-0 z-[-1] rounded-full bg-primary shadow-sm"
                      transition={morph}
                      initial={{ opacity: 0, scale: 0.92 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.92 }}
                    />
                  )}
                </AnimatePresence>
                <span>More</span>
                <ChevronDown
                  className={cn(
                    "h-3 w-3 opacity-80 transition-transform duration-200",
                    moreOpen && "rotate-180",
                  )}
                />
              </motion.button>

              {/* Hover dropdown — every category beyond the top 3 */}
              <AnimatePresence>
                {moreOpen && (
                  <motion.div
                    key="more-dropdown"
                    initial={reduce ? false : { opacity: 0, y: -6, scale: 0.97, filter: "blur(3px)" }}
                    animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
                    exit={{ opacity: 0, y: -4, scale: 0.97, filter: "blur(3px)" }}
                    transition={reduce ? { duration: 0 } : { type: "tween", ease: EASE, duration: 0.18 }}
                    className="glass-strong absolute right-0 top-full z-20 mt-2 max-h-80 w-56 origin-top-right overflow-y-auto rounded-2xl p-1.5"
                  >
                    {moreChips.map((cat) => {
                      const id = cat.id === "__all" ? null : cat.id;
                      const active = id === value;
                      return (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => {
                            onCategoryChange(id);
                            setMoreOpen(false);
                          }}
                          aria-pressed={active}
                          className={cn(
                            "flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs font-medium transition-colors",
                            active ? "bg-accent text-foreground" : "text-foreground hover:bg-accent/60",
                          )}
                        >
                          {cat.icon && <span className="opacity-80">{cat.icon}</span>}
                          <span className="min-w-0 flex-1 truncate">{cat.label}</span>
                          {typeof cat.count === "number" && (
                            <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                              {cat.count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </motion.div>
      </LayoutGroup>
    </div>
  );
};
