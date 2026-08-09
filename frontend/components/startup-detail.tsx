"use client";

import * as React from "react";
import { ExternalLink, FolderGit2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusPill, initials } from "@/components/startup-card";
import { formatDate, titleCase } from "@/lib/format";
import type { Startup } from "@/lib/types";

/** Detail modal: full description, metadata grid, links, and same-category peers. */
export function StartupDetail({
  startup,
  startups,
  onClose,
  onNavigate,
  onVerified,
}: {
  startup: Startup | null;
  startups: Startup[];
  onClose: () => void;
  onNavigate: (s: Startup) => void;
  onVerified?: (s: Startup) => void;
}) {
  const similar = React.useMemo(() => {
    if (!startup) return [];
    return startups
      .filter((s) => s.category === startup.category && s.id !== startup.id)
      .slice(0, 4);
  }, [startups, startup]);

  const open = startup !== null;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      {startup && (
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <div className="flex items-center gap-2.5 pr-12">
              <Avatar className="h-8 w-8 rounded-md bg-muted">
                <AvatarFallback className="rounded-md text-sm font-bold">
                  {initials(startup.name)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <DialogTitle className="text-base">{startup.name}</DialogTitle>
                <DialogDescription className="text-xs">
                  {startup.tagline || "No tagline yet"}
                </DialogDescription>
              </div>
              <StatusPill startup={startup} />
            </div>
          </DialogHeader>

          <div className="space-y-4">
            {startup.description && (
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                {startup.description}
              </p>
            )}

            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              {startup.founded && (
                <>
                  <dt className="text-muted-foreground">Founded</dt>
                  <dd className="font-medium">{formatDate(startup.founded)}</dd>
                </>
              )}
              {typeof startup.stars === "number" && startup.stars > 0 && (
                <>
                  <dt className="text-muted-foreground">Stars</dt>
                  <dd className="font-medium">{startup.stars.toLocaleString()}</dd>
                </>
              )}
              {startup.language && (
                <>
                  <dt className="text-muted-foreground">Language</dt>
                  <dd className="font-medium">{titleCase(startup.language)}</dd>
                </>
              )}
              {startup.category && (
                <>
                  <dt className="text-muted-foreground">Category</dt>
                  <dd className="font-medium">{titleCase(startup.category)}</dd>
                </>
              )}
              {startup.source && (
                <>
                  <dt className="text-muted-foreground">Source</dt>
                  <dd className="font-medium">{titleCase(startup.source)}</dd>
                </>
              )}
              <dt className="text-muted-foreground">Status</dt>
              <dd className="font-medium">
                {startup.status === "dead" || startup.status === "pivoted"
                  ? "Dead"
                  : startup.verified === 1
                    ? "Verified"
                    : "Unverified"}
              </dd>
              {startup.verified_at && (
                <>
                  <dt className="text-muted-foreground">Verified</dt>
                  <dd className="font-medium">{formatDate(startup.verified_at)}</dd>
                </>
              )}
              {startup.last_checked && (
                <>
                  <dt className="text-muted-foreground">Last checked</dt>
                  <dd className="font-medium">{formatDate(startup.last_checked)}</dd>
                </>
              )}
            </dl>

            <div className="flex flex-wrap items-center gap-2">
              {startup.website_url && (
                <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                  <a href={startup.website_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-3 w-3" /> Website
                  </a>
                </Button>
              )}
              {startup.github_url && (
                <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                  <a href={startup.github_url} target="_blank" rel="noreferrer">
                    <FolderGit2 className="h-3 w-3" /> Code
                  </a>
                </Button>
              )}
              {startup.status !== "dead" &&
                startup.status !== "pivoted" &&
                startup.verified !== 1 && (
                  <Button
                    type="button"
                    size="sm"
                    className="ml-auto h-8 gap-1.5 text-xs"
                    onClick={() => onVerified?.(startup)}
                  >
                    <ShieldCheck className="h-3 w-3" /> Mark verified
                  </Button>
                )}
            </div>

            {similar.length > 0 && (
              <div className="space-y-2 border-t pt-3">
                <h4 className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                  Similar — {titleCase(startup.category)}
                </h4>
                <div className="space-y-1">
                  {similar.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => onNavigate(s)}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left transition-colors hover:bg-accent"
                    >
                      <Avatar className="h-5 w-5 rounded-md bg-muted">
                        <AvatarFallback className="rounded-md text-[10px] font-bold">
                          {initials(s.name)}
                        </AvatarFallback>
                      </Avatar>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-semibold">{s.name}</span>
                        <span className="block truncate text-[11px] text-muted-foreground">
                          {s.tagline || titleCase(s.category)}
                        </span>
                      </span>
                      {s.verified === 1 && (
                        <ShieldCheck className="h-3 w-3 shrink-0 text-emerald-600 dark:text-emerald-400" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      )}
    </Dialog>
  );
}
