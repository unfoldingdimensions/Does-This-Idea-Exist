"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Architectural datum header for Ledger exhibition mode.
 * Aligns with the ledger specimen rows, giving an authentic terminal feeling.
 */
export function LedgerTableHeader({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "mb-2 flex items-center justify-between gap-3 border-b border-border/50 bg-background/60 px-3.5 py-1.5 backdrop-blur-md font-mono text-[10px] tracking-wider uppercase text-muted-foreground select-none rounded-t-lg",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-primary/70 font-semibold">{"//"}</span>
        <span>ARCHIVAL ENTITY</span>
      </div>
      <div className="hidden sm:flex items-center gap-2">
        <span className="text-primary/70 font-semibold">{"//"}</span>
        <span>SECTOR & VINTAGE</span>
      </div>
      <div className="flex items-center gap-6 pr-1">
        <div className="flex items-center gap-2">
          <span className="text-primary/70 font-semibold">{"//"}</span>
          <span>STATUS METER</span>
        </div>
        <span className="w-12 text-right">ACTION</span>
      </div>
    </div>
  );
}
