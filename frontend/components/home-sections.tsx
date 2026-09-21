"use client";

import * as React from "react";
import { Archive, Clock3, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { HueAvatar } from "@/components/hue-avatar";
import { parseDbDate, titleCase } from "@/lib/format";
import { EASE } from "@/lib/motion";
import type { Startup } from "@/lib/types";

function Strip({
  title,
  icon,
  footnote,
  items,
  onNavigate,
}: {
  title: string;
  icon: React.ReactNode;
  footnote?: string;
  items: Startup[];
  onNavigate: (s: Startup) => void;
}) {
  const reduce = useReducedMotion();
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <div className="ledger-header pb-2">
        {icon} {title}
        {footnote && (
          <span className="ml-2 hidden font-sans text-[10px] font-normal normal-case tracking-normal text-muted-foreground/80 sm:inline">
            {footnote}
          </span>
        )}
      </div>
      <div data-lenis-prevent className="flex gap-2 overflow-x-auto pb-1">
        {items.map((s, i) => (
          <div
            key={s.id}
            className="deal-item flex min-w-0 flex-1 basis-0"
            style={
              {
                "--i": i,
                "--deal-tilt": i % 2 === 0 ? "-0.7deg" : "0.7deg",
              } as React.CSSProperties
            }
          >
            <motion.button
              type="button"
              // Scoped id: the grid card and detail panel share `startup-${id}`
              // for the card→dossier morph; this strip row used to claim the
              // same id while both were mounted, glitching the projection.
              layoutId={reduce ? undefined : `strip-startup-${s.id}`}
              transition={{ type: "tween", ease: EASE, duration: 0.35 }}
              onClick={() => onNavigate(s)}
              className="glass flex w-full min-w-0 items-center gap-2 rounded-xl px-3 py-2 text-left transition-colors hover:bg-accent/60"
            >
              <HueAvatar name={s.name} size="sm" />
              <span className="min-w-0">
                <span className="block truncate text-xs font-semibold">{s.name}</span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {s.tagline || titleCase(s.category)}
                </span>
              </span>
            </motion.button>
          </div>
        ))}
      </div>
    </section>
  );
}

/** Freshness highlights, shown only when no filters are active. */
export function HomeSections({
  startups,
  onNavigate,
}: {
  startups: Startup[];
  onNavigate: (s: Startup) => void;
}) {
  const ts = (iso: string | null | undefined) => parseDbDate(iso)?.getTime() ?? 0;
  const justAdded = [...startups]
    .sort((a, b) => ts(b.created_at) - ts(a.created_at))
    .slice(0, 4);
  const recentlyVerified = startups
    .filter((s) => s.verified === 1 && s.verified_at)
    .sort((a, b) => ts(b.verified_at) - ts(a.verified_at))
    .slice(0, 4);
  // "Dead recently" must actually be recent: the backend returns dead entries
  // first in name order, so an unsorted slice shows the alphabetically-first
  // filings, not the newest deaths. Sort by last_checked (when the final
  // failing check landed), then created_at as a fallback.
  const deadRecently = startups
    .filter((s) => s.status === "dead" || s.status === "pivoted")
    .sort((a, b) => ts(b.last_checked) - ts(a.last_checked) || ts(b.created_at) - ts(a.created_at))
    .slice(0, 4);

  return (
    <div className="space-y-4 pb-6">
      <Strip
        title="Just added"
        icon={<Clock3 className="h-3 w-3" />}
        items={justAdded}
        onNavigate={onNavigate}
      />
      <Strip
        title="Recently verified"
        icon={<ShieldCheck className="h-3 w-3" />}
        footnote="Human-checks and machine approvals, newest first."
        items={recentlyVerified}
        onNavigate={onNavigate}
      />
      <Strip
        title="Dead recently"
        icon={<Archive className="h-3 w-3" />}
        footnote="Three failed checks. Filed, never deleted."
        items={deadRecently}
        onNavigate={onNavigate}
      />
    </div>
  );
}
