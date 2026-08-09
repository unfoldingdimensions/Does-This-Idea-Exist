"use client";

import * as React from "react";
import { ExternalLink, FolderGit2, Star, ShieldCheck, Archive } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HueAvatar } from "@/components/hue-avatar";
import type { Startup } from "@/lib/types";
import { foundedYear } from "@/lib/search";
import { formatDate, shortDate, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

export { initials } from "@/lib/initials";

/**
 * Status pill with a 6px status dot + worded tooltip — the trust layer as
 * visible card copy (research memo R-1/R-24). The Unverified pill is the
 * "Mark verified" affordance: click it to confirm the startup exists.
 * Verified copy uses the full date and never wraps mid-date (R-3 voice).
 */
export function StatusPill({
  startup,
  onMarkVerified,
}: {
  startup: Startup;
  onMarkVerified?: (s: Startup) => void;
}) {
  const dead = startup.status === "dead" || startup.status === "pivoted";
  const verified = !dead && startup.verified === 1;

  // Two-step confirm for the human-gate action: first click arms ("Confirm?"),
  // second click verifies; auto-disarms after 4s so a stray click can't flip
  // an entry's status (critique P2 — trust actions need a confirmation beat).
  const [confirming, setConfirming] = React.useState(false);
  const confirmTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(() => {
    return () => {
      if (confirmTimer.current) clearTimeout(confirmTimer.current);
    };
  }, []);

  const armConfirm = () => {
    if (confirming) return;
    setConfirming(true);
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
    confirmTimer.current = setTimeout(() => setConfirming(false), 4000);
  };

  const label = dead ? "Dead" : verified ? "Verified" : confirming ? "Confirm?" : "Unverified";
  const hint = dead
    ? "Checked 3 times, link dead each time. Filed, never deleted."
    : verified
      ? startup.verified_at
        ? `A human checked this on ${formatDate(startup.verified_at)} — it's alive.`
        : "A human checked this one. It's alive."
      : confirming
        ? "Click again to confirm — this stamps the entry as human-verified."
        : "Not yet confirmed — click to verify it.";

  const pillClass = cn(
    "gap-1.5 text-[11px]",
    dead && "border-destructive/20 bg-destructive/10 text-destructive",
    verified && "border-success/25 bg-success/12 text-success dark:bg-success/15 dark:text-success",
    !dead && !verified && "text-muted-foreground",
  );

  // Unverified → the pill is a button (mark-verified affordance, two-step).
  if (!dead && !verified && onMarkVerified) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={() => (confirming ? onMarkVerified(startup) : armConfirm())}
              className={cn(
                "inline-flex items-center rounded-full border bg-secondary/60 px-2.5 py-0.5 text-[11px] font-medium transition-colors",
                confirming
                  ? "border-primary/50 text-foreground"
                  : "hover:border-primary/40 hover:text-foreground",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "mr-1.5 size-1.5 rounded-full",
                  confirming ? "bg-primary" : "bg-muted-foreground/60",
                )}
              />
              {label}
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[90vw] whitespace-nowrap text-xs">
            {hint}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant="secondary" className={pillClass}>
            <span
              aria-hidden
              className={cn(
                "size-1.5 rounded-full",
                dead && "bg-destructive",
                verified && "bg-success",
              )}
            />
            {dead ? <Archive className="h-3 w-3" /> : verified ? <ShieldCheck className="h-3 w-3" /> : null}
            {label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[90vw] whitespace-nowrap text-xs">
          {hint}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function StartupCard({
  startup,
  onVerified,
  onDetails,
}: {
  startup: Startup;
  onVerified?: (s: Startup) => void;
  onDetails?: (s: Startup) => void;
}) {
  const dead = startup.status === "dead" || startup.status === "pivoted";
  const year = foundedYear(startup.founded);
  const [expanded, setExpanded] = React.useState(false);
  const description = startup.description ?? "";
  const showToggle = description.length > 140;
  const reduce = useReducedMotion();

  // Clamped (3-line) height of the description, measured on first toggle so the
  // expand/collapse animates between the preview and the full text instead of
  // snapping (the container clips; line-clamp only governs the collapsed state).
  const descRef = React.useRef<HTMLDivElement>(null);
  const [clampedH, setClampedH] = React.useState<number | undefined>(undefined);

  const toggleDescription = () => {
    const el = descRef.current;
    if (el && clampedH === undefined) {
      setClampedH(el.getBoundingClientRect().height);
    }
    setExpanded((v) => !v);
  };

  return (
    <motion.div
      layoutId={`startup-${startup.id}`}
      whileHover={reduce ? undefined : { y: -2 }}
      whileTap={reduce ? undefined : { scale: 0.99 }}
      transition={{ type: "tween", ease: [0.22, 1, 0.36, 1], duration: 0.35 }}
      className={cn("glass flex h-full flex-col rounded-2xl", dead && "opacity-85 saturate-[0.55]")}
    >
      <div className="flex h-full flex-col gap-2.5 p-4">
        <div className="flex items-center gap-2.5">
          <HueAvatar name={startup.name} />
          <div className="min-w-0 flex-1">
            <button
              type="button"
              onClick={() => onDetails?.(startup)}
              className="truncate text-left text-sm font-bold leading-tight hover:text-primary hover:underline"
              title="View details"
            >
              {startup.name}
            </button>
            <p className="truncate font-mono text-[11px] tabular-nums text-muted-foreground">
              {year && <>founded {year}</>}
              {year && startup.last_checked && <span className="text-border"> · </span>}
              {startup.last_checked && <>checked {shortDate(startup.last_checked)}</>}
            </p>
          </div>
          <StatusPill startup={startup} onMarkVerified={onVerified} />
        </div>

        {startup.tagline && (
          <p className="line-clamp-2 min-h-9 text-[13px] font-medium leading-snug">
            {startup.tagline}
          </p>
        )}

        {description && (
          <div className="space-y-1">
            <motion.div
              ref={descRef}
              initial={false}
              animate={{ height: expanded ? "auto" : clampedH }}
              transition={
                reduce
                  ? { duration: 0 }
                  : { type: "tween", ease: [0.22, 1, 0.36, 1], duration: 0.32 }
              }
              className="overflow-hidden"
            >
              <p
                className={cn(
                  "text-[13px] leading-relaxed text-muted-foreground",
                  !expanded && "line-clamp-3",
                )}
              >
                {description}
              </p>
            </motion.div>
            {showToggle && (
              <button
                type="button"
                onClick={toggleDescription}
                aria-expanded={expanded}
                className="text-xs font-medium text-primary hover:underline"
              >
                {expanded ? "Show less" : "Show more"}
              </button>
            )}
          </div>
        )}

        <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
          {startup.category && (
            <Badge variant="secondary" className="text-[11px]">
              {titleCase(startup.category)}
            </Badge>
          )}
          {startup.language && (
            <Badge variant="outline" className="text-[11px]">
              {titleCase(startup.language)}
            </Badge>
          )}
          {typeof startup.stars === "number" && startup.stars > 0 && (
            <span className="ml-auto flex items-center gap-1 font-mono text-[11px] tabular-nums text-muted-foreground">
              <Star className="h-3 w-3" /> {startup.stars.toLocaleString()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-border/60 pt-3">
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
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="ml-auto h-8 gap-1.5 text-xs"
            onClick={() => onDetails?.(startup)}
          >
            Details
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
