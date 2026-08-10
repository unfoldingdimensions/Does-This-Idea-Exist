"use client";

import * as React from "react";
import { Check, ExternalLink, FolderGit2, Star, ShieldCheck, Archive } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { HueAvatar } from "@/components/hue-avatar";
import type { Startup } from "@/lib/types";
import { foundedYear } from "@/lib/search";
import { formatDate, shortDate, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

export { initials } from "@/lib/initials";

export type StatusChoice = "verified" | "unverified" | "dead";

const STATUS_OPTIONS: {
  value: StatusChoice;
  label: string;
  hint: string;
}[] = [
  {
    value: "verified",
    label: "Verified",
    hint: "A human checked this one. It's alive.",
  },
  {
    value: "unverified",
    label: "Unverified",
    hint: "Filed, awaiting a human.",
  },
  {
    value: "dead",
    label: "Dead",
    hint: "Checked, gone. Filed, never deleted.",
  },
];

/** Copy for the themed confirm dialog, keyed by the choice being applied. */
const CONFIRM_COPY: Record<
  StatusChoice,
  { title: (name: string) => string; body: (name: string) => string }
> = {
  verified: {
    title: (name) => `Mark ${name} as verified?`,
    body: (name) =>
      `Stamps ${name} as human-checked and alive. This is reversible — you can unverify it later.`,
  },
  unverified: {
    title: (name) => `Mark ${name} as unverified?`,
    body: (name) =>
      `Clears the verified stamp on ${name}. It returns to "filed, awaiting a human".`,
  },
  dead: {
    title: (name) => `Mark ${name} as dead?`,
    body: (name) =>
      `Files ${name} as dead — checked and gone. It stays in the archive, never deleted.`,
  },
};

/**
 * Status pill with a 6px status dot + worded tooltip — the trust layer as
 * visible card copy (research memo R-1/R-24). When `onStatusChange` is wired
 * the pill is a button in every state: clicking it opens a small menu with the
 * three trust states (Verified / Unverified / Dead); picking one raises a
 * themed confirm dialog so the human gate never flips on a stray click.
 */
export function StatusPill({
  startup,
  onStatusChange,
}: {
  startup: Startup;
  onStatusChange?: (s: Startup, choice: StatusChoice) => void;
}) {
  const dead = startup.status === "dead" || startup.status === "pivoted";
  const verified = !dead && startup.verified === 1;
  const current: StatusChoice = dead ? "dead" : verified ? "verified" : "unverified";

  const [menuOpen, setMenuOpen] = React.useState(false);
  const [pending, setPending] = React.useState<StatusChoice | null>(null);

  const label = STATUS_OPTIONS.find((o) => o.value === current)?.label ?? "Unverified";
  const hint = dead
    ? "Checked 3 times, link dead each time. Filed, never deleted."
    : verified
      ? startup.verified_at
        ? `A human checked this on ${formatDate(startup.verified_at)} — it's alive.`
        : "A human checked this one. It's alive."
      : "Not yet confirmed — click to change its status.";

  const pillClass = cn(
    "gap-1.5 text-[11px]",
    dead && "border-destructive/20 bg-destructive/10 text-destructive",
    verified && "border-success/25 bg-success/12 text-success dark:bg-success/15 dark:text-success",
    !dead && !verified && "text-muted-foreground",
  );

  const confirm = pending ? CONFIRM_COPY[pending] : null;

  // No status handler → the pill is a plain badge (read-only context).
  if (!onStatusChange) {
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
                  !dead && !verified && "bg-muted-foreground/60",
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

  return (
    <>
      <Popover open={menuOpen} onOpenChange={setMenuOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
              pillClass,
              "hover:border-primary/40 hover:text-foreground",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "size-1.5 rounded-full",
                dead && "bg-destructive",
                verified && "bg-success",
                !dead && !verified && "bg-muted-foreground/60",
              )}
            />
            {dead ? <Archive className="h-3 w-3" /> : verified ? <ShieldCheck className="h-3 w-3" /> : null}
            {label}
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" sideOffset={6} className="w-44 p-1">
          <div className="px-2.5 pb-1.5 pt-1 text-[11px] text-muted-foreground">{hint}</div>
          <div role="menu" className="flex flex-col gap-0.5">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  setPending(opt.value);
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs font-medium transition-colors",
                  opt.value === current
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "size-1.5 rounded-full",
                    opt.value === "dead" && "bg-destructive",
                    opt.value === "verified" && "bg-success",
                    opt.value === "unverified" && "bg-muted-foreground/60",
                  )}
                />
                {opt.label}
                {opt.value === current && <Check className="ml-auto h-3 w-3" />}
              </button>
            ))}
          </div>
        </PopoverContent>
      </Popover>

      <Dialog open={pending !== null} onOpenChange={(o) => !o && setPending(null)}>
        <DialogContent className="sm:max-w-sm" showCloseButton={false}>
          {confirm && (
            <>
              <DialogHeader>
                <DialogTitle>{confirm.title(startup.name)}</DialogTitle>
                <DialogDescription>{confirm.body(startup.name)}</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setPending(null)}>
                  Discard
                </Button>
                <Button
                  variant={pending === "dead" ? "destructive" : "default"}
                  onClick={() => {
                    if (pending) onStatusChange(startup, pending);
                    setPending(null);
                  }}
                >
                  {pending === "dead" ? "File as dead" : pending === "unverified" ? "Clear stamp" : "Confirm verified"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export function StartupCard({
  startup,
  onStatusChange,
  onDetails,
}: {
  startup: Startup;
  onStatusChange?: (s: Startup, choice: StatusChoice) => void;
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
              className="block w-full truncate text-left text-sm font-bold leading-tight hover:text-primary hover:underline"
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
          <StatusPill startup={startup} onStatusChange={onStatusChange} />
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
