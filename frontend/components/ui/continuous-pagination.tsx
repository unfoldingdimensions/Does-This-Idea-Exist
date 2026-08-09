"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * Continuous pagination — controlled page control with a sliding active pill
 * (shared-layout) and ease-out motion. Adapted from Watermelon UI (MIT):
 * framer-motion → motion/react, springs → ease-out (antislop), tokens → glass.
 */
export interface ContinuousPaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const EASE = [0.22, 1, 0.36, 1] as const;

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

export function ContinuousPagination({ page, totalPages, onPageChange }: ContinuousPaginationProps) {
  if (totalPages <= 1) return null;
  const pages = pageWindow(page, totalPages);

  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-1.5 py-8">
      <button
        type="button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
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
              aria-current={p === page ? "page" : undefined}
              className={cn(
                "relative z-10 flex h-11 w-11 items-center justify-center rounded-full text-sm font-medium transition-colors",
                p === page
                  ? "bg-primary font-bold text-primary-foreground"
                  : "glass text-foreground hover:bg-accent",
              )}
              whileHover={p === page ? undefined : { y: -2 }}
              whileTap={{ scale: 0.94 }}
              transition={{ type: "tween", ease: EASE, duration: 0.18 }}
            >
              {p}
            </motion.button>
          ),
        )}
      </div>

      <button
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Next page"
        className="glass flex h-11 w-11 items-center justify-center rounded-full text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}
