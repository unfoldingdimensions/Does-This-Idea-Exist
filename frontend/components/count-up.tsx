"use client";

import * as React from "react";
import { useReducedMotion } from "motion/react";

/**
 * Animated count-up on value change — the NumberFlow replacement.
 * NumberFlow's <script>-based SSR render is incompatible with React 19
 * (renders an empty custom element + dev warning), so we roll the same
 * effect: rAF + easeOutCubic + tabular numerals.
 *
 * Counts from the PREVIOUS value, never from 0 (every verify used to flip
 * the footer back to zero and recount the archive). Reduced-motion readers
 * get the final value directly — no animation state, so the count always
 * updates instead of freezing at its mount value.
 */
export function CountUp({
  value,
  duration = 600,
  className,
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = React.useState(value);
  const prevRef = React.useRef(value);

  React.useEffect(() => {
    if (reduce) return; // reduced-motion render path shows `value` directly
    const from = prevRef.current;
    prevRef.current = value;
    if (from === value) return; // no change (incl. first mount — already displayed)
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setDisplay(Math.round(from + (value - from) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration, reduce]);

  return (
    <span className={className} aria-label={value.toLocaleString()}>
      {(reduce ? value : display).toLocaleString()}
    </span>
  );
}
