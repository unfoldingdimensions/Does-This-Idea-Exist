"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface BorderBeamProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: number;
  duration?: number;
  borderWidth?: number;
  anchor?: number;
  colorFrom?: string;
  colorTo?: string;
  delay?: number;
}

/**
 * BorderBeam — Sourced from Magic UI (MIT License).
 * An animated perimeter beam that moves around the border of a container.
 * Lightweight, hardware-accelerated, and cleanly disabled under prefers-reduced-motion.
 */
export function BorderBeam({
  className,
  size = 150,
  duration = 8,
  anchor = 90,
  borderWidth = 1.5,
  colorFrom = "var(--primary)",
  colorTo = "var(--accent-gold, #f59e0b)",
  delay = 0,
  ...props
}: BorderBeamProps) {
  return (
    <div
      style={
        {
          "--size": `${size}px`,
          "--duration": `${duration}s`,
          "--anchor": `${anchor}%`,
          "--border-width": `${borderWidth}px`,
          "--color-from": colorFrom,
          "--color-to": colorTo,
          "--delay": `-${delay}s`,
        } as React.CSSProperties
      }
      className={cn(
        "pointer-events-none absolute inset-0 rounded-[inherit] [border:calc(var(--border-width)*1px)_solid_transparent]",
        "![mask-clip:padding-box,border-box] ![mask-composite:intersect] [mask:linear-gradient(transparent,transparent),linear-gradient(white,white)]",
        "after:absolute after:aspect-square after:w-[calc(var(--size)*1px)] after:animate-border-beam after:[animation-delay:var(--delay)] after:[background:linear-gradient(to_left,var(--color-from),var(--color-to),transparent)] after:[offset-anchor:calc(var(--anchor)*1%)_50%] after:[offset-path:rect(0_auto_auto_0_round_calc(var(--size)*1px))]",
        "motion-reduce:after:animate-none motion-reduce:after:opacity-0",
        className
      )}
      {...props}
    />
  );
}
