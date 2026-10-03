"use client";

import { OdometerNumber } from "@/components/ui/odometer-number";
import { formatDate } from "@/lib/format";
import type { Stats } from "@/lib/types";

interface LiveTelemetryBarProps {
  stats: Stats | null;
  className?: string;
}

/**
 * The archive's status strip — REAL numbers only.
 *
 * This used to cycle six hardcoded ping records ("Stripe 14ms 200", "Vercel
 * 12ms") under an "Archive Radar / SWEEP ACTIVE" badge, with a blinking ping dot
 * and an endlessly animating oscilloscope trace. On a product whose whole
 * position is verification-first, that was invented liveness sitting directly
 * above the real counts and borrowing their credibility — a reader asking "how
 * do you know?" got no answer. The trace also ran forever, against the
 * Micro-Delight Rule.
 *
 * What replaces it is the thing the bar was imitating: the date the archive last
 * checked itself, plus the three counts that actually exist (filed, verified
 * alive, dead). When `last_checked` is null the strip says so rather than
 * decorating the absence.
 */
export function LiveTelemetryBar({ stats, className }: LiveTelemetryBarProps) {
  const checked = stats?.last_checked ? formatDate(stats.last_checked) : null;
  // The four counts must ADD UP to what is filed: verified + dead + unverified.
  // Showing only three of them left four entries unaccounted for, which on this
  // product reads as a rounding error in the trust layer.
  const total = stats?.total ?? 0;
  const verified = stats?.verified ?? 0;
  const dead = stats?.dead ?? 0;
  const unverified = Math.max(0, total - verified - dead);

  return (
    <div
      className={
        "relative mx-auto w-full max-w-4xl overflow-hidden rounded-2xl border border-border/40 bg-background/40 p-2.5 backdrop-blur-xl " +
        (className ?? "")
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-2">
        <span className="font-mono text-xs text-muted-foreground">
          {checked ? (
            <>
              Last check <span className="tabular-nums text-foreground/80">{checked}</span>
            </>
          ) : (
            "Not checked yet"
          )}
        </span>

        <div className="flex items-center gap-4">
          <Stat label="Filed" value={total} />
          <span className="h-6 w-px bg-border/60" />
          <Stat label="Verified" value={verified} tone="success" />
          <span className="h-6 w-px bg-border/60" />
          <Stat label="Unverified" value={unverified} />
          <span className="h-6 w-px bg-border/60" />
          <Stat label="Dead" value={dead} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "success" }) {
  return (
    <span className="flex flex-col items-end">
      <span className="font-mono text-xs font-bold tracking-widest whitespace-nowrap text-muted-foreground uppercase">
        {label}
      </span>
      <span
        className={
          "font-mono text-xs font-bold " + (tone === "success" ? "text-success" : "text-foreground")
        }
      >
        <OdometerNumber value={value} />
      </span>
    </span>
  );
}
