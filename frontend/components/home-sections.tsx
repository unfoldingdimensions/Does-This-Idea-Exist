"use client";

import * as React from "react";
import { Archive, Clock3, ShieldCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/components/startup-card";
import { titleCase } from "@/lib/format";
import type { Startup } from "@/lib/types";

function Strip({
  title,
  icon,
  items,
  onNavigate,
}: {
  title: string;
  icon: React.ReactNode;
  items: Startup[];
  onNavigate: (s: Startup) => void;
}) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {icon} {title}
      </h3>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {items.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onNavigate(s)}
            className="flex min-w-0 flex-1 basis-0 items-center gap-2 rounded-xl border bg-card px-3 py-2 text-left transition-colors hover:bg-accent"
          >
            <Avatar className="h-6 w-6 shrink-0 rounded-md bg-muted">
              <AvatarFallback className="rounded-md text-[10px] font-bold">
                {initials(s.name)}
              </AvatarFallback>
            </Avatar>
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
      <Strip title="Just added" icon={<Clock3 className="h-3 w-3" />} items={justAdded} onNavigate={onNavigate} />
      <Strip title="Recently verified" icon={<ShieldCheck className="h-3 w-3" />} items={recentlyVerified} onNavigate={onNavigate} />
      <Strip title="Dead recently" icon={<Archive className="h-3 w-3" />} items={deadRecently} onNavigate={onNavigate} />
    </div>
  );
}
