"use client";

import * as React from "react";
import { Radio } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { OdometerNumber } from "@/components/ui/odometer-number";
import type { Stats } from "@/lib/types";

interface LiveTelemetryBarProps {
  stats: Stats | null;
  className?: string;
}

const RECENT_PINGS = [
  { name: "Stripe", latency: "14ms", status: "alive", code: 200 },
  { name: "Supabase", latency: "22ms", status: "alive", code: 200 },
  { name: "Linear", latency: "18ms", status: "alive", code: 200 },
  { name: "Resend", latency: "19ms", status: "alive", code: 200 },
  { name: "Vercel", latency: "12ms", status: "alive", code: 200 },
  { name: "Cursor", latency: "25ms", status: "alive", code: 200 },
];

export function LiveTelemetryBar({ stats, className }: LiveTelemetryBarProps) {
  const reduce = useReducedMotion();
  const [activePingIdx, setActivePingIdx] = React.useState(0);
  const [pingPulse, setPingPulse] = React.useState(false);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setActivePingIdx((prev) => (prev + 1) % RECENT_PINGS.length);
      setPingPulse(true);
      setTimeout(() => setPingPulse(false), 300);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  const currentPing = RECENT_PINGS[activePingIdx];

  return (
    <div
      className={
        "group relative mx-auto w-full max-w-4xl overflow-hidden rounded-2xl border border-border/40 bg-background/40 p-2.5 backdrop-blur-xl transition-all duration-300 hover:border-primary/40 hover:bg-background/60 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] dark:hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)] " +
        (className ?? "")
      }
    >
      {/* Subtle background radar scanline */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"
      />

      <div className="flex flex-wrap items-center justify-between gap-3 px-2">
        {/* Left: Oscilloscope Pulse & Heartbeat Status */}
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-6 w-6 items-center justify-center rounded-lg border border-success/30 bg-success/10 text-success">
            <Radio className="h-3.5 w-3.5 animate-pulse" />
            <span
              className={
                "absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-success transition-transform " +
                (pingPulse ? "scale-150" : "scale-100")
              }
            />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Archive Radar
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-1.5 py-0.2 text-[9px] font-semibold text-success">
                <span className="h-1 w-1 rounded-full bg-success animate-ping" />
                SWEEP ACTIVE
              </span>
            </div>
            <span className="font-mono text-[11px] tabular-nums text-foreground/80">
              Latency: <span className="font-semibold text-success">{currentPing.latency}</span>
              <span className="text-border"> · </span>
              Target: <span className="font-medium">{currentPing.name}</span> ({currentPing.code})
            </span>
          </div>
        </div>

        {/* Center: Live Waveform Visualizer (SVG) */}
        <div className="hidden h-6 w-36 items-center md:flex" aria-hidden>
          <svg
            className="h-full w-full text-primary/60"
            viewBox="0 0 120 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <motion.path
              d="M0 12 H30 L35 4 L42 20 L48 8 L54 16 L58 12 H120"
              initial={{ pathOffset: 0 }}
              animate={reduce ? undefined : { pathOffset: [0, 1] }}
              transition={{ repeat: Infinity, duration: 2.2, ease: "linear" }}
              strokeDasharray="120"
            />
          </svg>
        </div>

        {/* Right: Specimen Totals in Rolling Drum Digits */}
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
              Total Filings
            </span>
            <span className="font-mono text-xs font-bold text-foreground">
              <OdometerNumber value={stats?.total ?? 0} />
            </span>
          </div>

          <div className="h-6 w-px bg-border/60" />

          <div className="flex flex-col items-end">
            <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
              Verified Alive
            </span>
            <span className="font-mono text-xs font-bold text-success">
              <OdometerNumber value={stats?.verified ?? 0} />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
