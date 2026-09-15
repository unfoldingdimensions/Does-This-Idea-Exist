"use client";

import * as React from "react";
import { Compass, RotateCcw, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  onResetFilters?: () => void;
  onOpenSubmit?: () => void;
  className?: string;
}

/**
 * Archival Empty State adhering to the ui-design-sourcing-skill:
 * "Icon + title + explanation + action (never a bare No data)"
 */
export function EmptyState({
  title = "NO ARCHIVAL FILINGS MATCH CRITERIA",
  description = "The vault scanned 2,282 active and historical startups, but found zero records matching your current filter coordinates.",
  onResetFilters,
  onOpenSubmit,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "relative flex w-full flex-col items-center justify-center rounded-2xl border border-dashed border-border/70 bg-card/20 px-6 py-16 text-center backdrop-blur-md",
        className
      )}
      role="status"
      aria-live="polite"
    >
      {/* Radar Coordinate Crosshair Icon */}
      <div className="relative mb-5 flex size-16 items-center justify-center rounded-2xl border border-border/60 bg-background/80 shadow-inner">
        <Compass className="size-8 text-primary/70 animate-[spin_12s_linear_infinite] motion-reduce:animate-none" />
        <span className="absolute -top-1 -right-1 flex size-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex size-2.5 rounded-full bg-amber-500" />
        </span>
      </div>

      <div className="font-mono text-[11px] tracking-widest uppercase text-muted-foreground mb-1">
        {"// COORDINATE STATUS: 0 MATCHES"}
      </div>

      <h3 className="font-display text-base sm:text-lg font-bold text-foreground max-w-md">
        {title}
      </h3>

      <p className="mt-2 max-w-md text-xs text-muted-foreground leading-relaxed">
        {description}
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {onResetFilters && (
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={() => {
              sound.playTick();
              onResetFilters();
            }}
            className="h-8 gap-2 rounded-full px-4 text-xs font-medium cursor-pointer"
          >
            <RotateCcw className="size-3.5" />
            Reset All Filters
          </Button>
        )}
        {onOpenSubmit && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              sound.playTick();
              onOpenSubmit();
            }}
            className="h-8 gap-2 rounded-full px-4 text-xs font-medium cursor-pointer"
          >
            <PlusCircle className="size-3.5" />
            Submit New Entity
          </Button>
        )}
      </div>
    </div>
  );
}
