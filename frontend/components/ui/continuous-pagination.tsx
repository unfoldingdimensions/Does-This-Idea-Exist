"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { tween, EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Continuous pagination — windowed page control with a shared-layout active
 * pill that slides between pages (the docstring finally matches the code).
 * The layoutId lives on a SIBLING span, never the button: layout projection
 * writes an inline transparent box-shadow that would clobber the button's
 * focus ring (the same reason .search-focus-ring is hand-written CSS).
 */
export interface ContinuousPaginationProps {
  /** The clamped page the grid actually shows — never the raw URL value. */
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

/** Windowed page list: 1 … (p-1) p (p+1) … total — never more than ~7 buttons. */
function pageWindow(page: number, totalPages: number): (number | "…")[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  const set = new Set<number>([1, totalPages, page - 1, page, page + 1]);
  const nums = [...set].filter((n) => n >= 1 && n <= totalPages).sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  let prev = 0;
  for (const n of nums) {
    if (n - prev > 1) out.push("…");
    out.push(n);
    prev = n;
  }
  return out;
}

export function ContinuousPagination({ currentPage, totalPages, onPageChange }: ContinuousPaginationProps) {
  if (totalPages <= 1) return null;
  const pages = pageWindow(currentPage, totalPages);

  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-1.5 py-8">
      <button
        type="button"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        aria-label="Previous page"
        className="glass flex h-11 w-11 items-center justify-center rounded-full text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div className="flex items-center gap-1.5 px-1">
        {pages.map((p, i) =>
          p === "…" ? (
            <span key={`ellipsis-${i}`} aria-hidden className="px-1 font-mono text-xs text-muted-foreground">
              …
            </span>
          ) : (
            <motion.button
              key={p}
              type="button"
              onClick={() => onPageChange(p)}
              aria-label={`Page ${p}`}
              aria-current={p === currentPage ? "page" : undefined}
              className={cn(
                "relative flex h-11 w-11 items-center justify-center rounded-full text-sm font-medium transition-colors",
                p === currentPage ? "font-bold text-primary-foreground" : "glass text-foreground hover:bg-accent",
              )}
              whileHover={p === currentPage ? undefined : { y: -2 }}
              whileTap={{ scale: 0.94 }}
              transition={{ type: "tween", ease: EASE, duration: 0.18 }}
            >
              <AnimatePresence initial={false}>
                {p === currentPage && (
                  <motion.span
                    layoutId="pagination-pill"
                    className="absolute inset-0 rounded-full bg-primary"
                    transition={tween(0.3)}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  />
                )}
              </AnimatePresence>
              <span className="relative z-10">{p}</span>
            </motion.button>
          ),
        )}
      </div>

      <button
        type="button"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        aria-label="Next page"
        className="glass flex h-11 w-11 items-center justify-center rounded-full text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}
