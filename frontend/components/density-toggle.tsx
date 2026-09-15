"use client";

import * as React from "react";
import { LayoutGrid, ListFilter } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

export type DensityMode = "gallery" | "ledger";

interface DensityToggleProps {
  value: DensityMode;
  onChange: (mode: DensityMode) => void;
  className?: string;
}

export function DensityToggle({ value, onChange, className }: DensityToggleProps) {
  const reduce = useReducedMotion();

  const handleSelect = (mode: DensityMode) => {
    if (mode !== value) {
      sound.playTick();
      onChange(mode);
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label="Exhibition density"
      className={cn(
        "inline-flex items-center gap-0.5 rounded-full border border-border/50 bg-background/50 p-0.5 backdrop-blur-md",
        className,
      )}
    >
      <button
        type="button"
        role="radio"
        aria-checked={value === "gallery"}
        onClick={() => handleSelect("gallery")}
        className={cn(
          "relative flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
          value === "gallery" ? "text-primary-foreground font-semibold" : "text-muted-foreground hover:text-foreground",
        )}
        title="Gallery mode: 3D Holographic Specimen Cards"
      >
        {value === "gallery" && (
          <motion.div
            layoutId="density-pill"
            transition={
              reduce
                ? { duration: 0 }
                : { type: "spring", stiffness: 380, damping: 28 }
            }
            className="absolute inset-0 rounded-full bg-primary"
          />
        )}
        <span className="relative z-10 flex items-center gap-1.5">
          <LayoutGrid className="h-3 w-3" />
          <span className="hidden sm:inline">Gallery</span>
        </span>
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={value === "ledger"}
        onClick={() => handleSelect("ledger")}
        className={cn(
          "relative flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
          value === "ledger" ? "text-primary-foreground font-semibold" : "text-muted-foreground hover:text-foreground",
        )}
        title="Ledger mode: Dense Archival Specimen Rows"
      >
        {value === "ledger" && (
          <motion.div
            layoutId="density-pill"
            transition={
              reduce
                ? { duration: 0 }
                : { type: "spring", stiffness: 380, damping: 28 }
            }
            className="absolute inset-0 rounded-full bg-primary"
          />
        )}
        <span className="relative z-10 flex items-center gap-1.5">
          <ListFilter className="h-3 w-3" />
          <span className="hidden sm:inline">Ledger</span>
        </span>
      </button>
    </div>
  );
}
