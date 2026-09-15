"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

interface OdometerNumberProps {
  value: number;
  className?: string;
  format?: (n: number) => string;
}

function DigitColumn({ digit }: { digit: string }) {
  const reduce = useReducedMotion();
  const num = Number.parseInt(digit, 10);

  if (Number.isNaN(num)) {
    return <span className="inline-block">{digit}</span>;
  }

  return (
    <span className="relative inline-block h-[1.15em] w-[0.62em] overflow-hidden align-baseline tabular-nums">
      <motion.span
        className="absolute left-0 top-0 flex flex-col"
        initial={false}
        animate={{ y: `-${num * 10}%` }}
        transition={
          reduce
            ? { duration: 0 }
            : {
                type: "spring",
                stiffness: 280,
                damping: 24,
                mass: 0.8,
              }
        }
      >
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
          <span
            key={n}
            className="flex h-[1.15em] items-center justify-center font-mono leading-none"
          >
            {n}
          </span>
        ))}
      </motion.span>
    </span>
  );
}

export function OdometerNumber({ value, className, format }: OdometerNumberProps) {
  const str = format ? format(value) : value.toLocaleString();
  const chars = str.split("");

  return (
    <span className={cn("inline-flex items-baseline font-mono tabular-nums", className)} aria-label={str}>
      <span className="sr-only">{str}</span>
      <span aria-hidden="true" className="inline-flex items-baseline">
        {chars.map((ch, idx) => (
          <DigitColumn key={`${idx}-${chars.length}`} digit={ch} />
        ))}
      </span>
    </span>
  );
}

