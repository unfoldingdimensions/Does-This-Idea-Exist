"use client";

import * as React from "react";

/**
 * Animated count-up on value change — the NumberFlow replacement.
 * NumberFlow's <script>-based SSR render is incompatible with React 19
 * (renders an empty custom element + dev warning), so we roll the same
 * effect: rAF + easeOutCubic + tabular numerals + reduced-motion off.
 * Renders the final value initially (no layout shift / no-JS friendly),
 * then counts from 0 to it on mount.
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
  const [display, setDisplay] = React.useState(value);

  React.useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return; // stays at the final value — motion off
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setDisplay(Math.round(eased * value));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);

  return (
    <span className={className} aria-label={value.toLocaleString()}>
      {display.toLocaleString()}
    </span>
  );
}
