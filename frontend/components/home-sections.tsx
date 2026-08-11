"use client";

import * as React from "react";
import { Archive, Clock3, ShieldCheck } from "lucide-react";
import { HueAvatar } from "@/components/hue-avatar";
import { titleCase } from "@/lib/format";
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
      <div className="flex gap-2 overflow-x-auto pb-1">
        {items.map((s, i) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onNavigate(s)}
            className="deal-item glass flex min-w-0 flex-1 basis-0 items-center gap-2 rounded-xl px-3 py-2 text-left transition-colors hover:bg-accent/60"
            style={
              {
                "--i": i,
                "--deal-tilt": i % 2 === 0 ? "-0.7deg" : "0.7deg",
              } as React.CSSProperties
            }
          >
            <HueAvatar name={s.name} size="sm" />
            <span className="min-w-0">
              <span className="block truncate text-xs font-semibold">{s.name}</span>
              <span className="block truncate text-[11px] text-muted-foreground">
                {s.tagline || titleCase(s.category)}
              </span>
            </span>
          </button>
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
  const ts = (iso: string | null | undefined) => (iso ? new Date(iso).getTime() : 0);
  const justAdded = [...startups]
    .sort((a, b) => ts(b.created_at) - ts(a.created_at))
    .slice(0, 4);
  const recentlyVerified = startups
    .filter((s) => s.verified === 1 && s.verified_at)
    .sort((a, b) => ts(b.verified_at) - ts(a.verified_at))
    .slice(0, 4);
  const deadRecently = startups
    .filter((s) => s.status === "dead" || s.status === "pivoted")
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
