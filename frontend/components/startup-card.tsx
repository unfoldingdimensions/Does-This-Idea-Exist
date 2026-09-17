"use client";

import * as React from "react";
import { Check, ExternalLink, FolderGit2, Star, ShieldCheck, Archive } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { SPRING_SETTLE, SPRING_STAMP, EASE } from "@/lib/motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { HolographicCard } from "@/components/holographic-card";
import { StampChoreography } from "@/components/stamp-choreography";
import type { Startup } from "@/lib/types";
import { formatDate, foundedShort, shortDate, titleCase } from "@/lib/format";
import { useAdminToken } from "@/lib/use-admin-token";
import { cn } from "@/lib/utils";

export type StatusChoice = "verified" | "unverified" | "dead";

/**
 * Defense in depth for external links: the backend's `_http_url` strips
 * non-http(s) schemes at write time, but a row predating that guard (or edited
 * directly in the DB) must never become a click-to-execute `javascript:` sink.
 * The Website/Code buttons render only for http(s) URLs.
 */
function isHttpUrl(value: string | null | undefined): value is string {
  return typeof value === "string" && /^https?:\/\//i.test(value.trim());
}
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

  const unlocked = useAdminToken() !== null;
  const [menuOpen, setMenuOpen] = React.useState(false);
  const [hintOpen, setHintOpen] = React.useState(false);
  const [pending, setPending] = React.useState<StatusChoice | null>(null);
  const [justStamped, setJustStamped] = React.useState(false);
  const reduce = useReducedMotion();

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

  // Read-only context (visitor, or no status handler): the pill becomes an
  // informative button — keyboard/touch reachable (the old span-tooltip was
  // neither) — opening a popover with the worded hint + how verification works.
  if (!onStatusChange || !unlocked) {
    return (
      <Popover open={hintOpen} onOpenChange={setHintOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
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
        <PopoverContent align="end" sideOffset={6} className="w-64 p-3">
          <p className="text-xs leading-relaxed text-muted-foreground">{hint}</p>
          <p className="mt-2 border-t border-border/60 pt-2 text-[11px] leading-relaxed text-muted-foreground/80">
            How verification works: a human opens the link and stamps the filing. No crawlers,
            no votes — the stamp means someone looked.
          </p>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <>
      <Popover open={menuOpen} onOpenChange={setMenuOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            className={cn(
              "relative inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
              pillClass,
              "hover:border-primary/40 hover:text-foreground",
            )}
          >
            {/* One-shot sage ring on the verified transition — the stamp
                landing. Fires from the confirm click (justStamped), clears
                itself when the ring's animation completes. aria-hidden. */}
            {verified && (
              <motion.span
                key={`ring-${startup.id}`}
                aria-hidden
                initial={justStamped ? { scale: 1, opacity: 0.6 } : false}
                animate={{ scale: 2.4, opacity: 0 }}
                transition={reduce ? { duration: 0 } : { duration: 0.55, ease: "easeOut" }}
                onAnimationComplete={() => setJustStamped(false)}
                className="pointer-events-none absolute inset-0 rounded-full bg-success"
              />
            )}
            {/* Pill settle — plays when the curator's confirm lands. */}
            <motion.span
              key={`pill-${current}`}
              initial={justStamped ? { scale: 1.06 } : false}
              animate={{ scale: 1 }}
              transition={reduce ? { duration: 0 } : SPRING_SETTLE}
              className="inline-flex items-center gap-1.5"
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
              {dead ? (
                <Archive className="h-3 w-3" />
              ) : verified ? (
                <motion.span
                  key={`stamp-${current}`}
                  initial={justStamped ? { rotate: -12, scale: 0.6 } : false}
                  animate={{ rotate: 0, scale: 1 }}
                  transition={reduce ? { duration: 0 } : SPRING_STAMP}
                  className="inline-flex"
                >
                  <ShieldCheck className="h-3 w-3" />
                </motion.span>
              ) : null}
              {label}
            </motion.span>
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" sideOffset={6} className="w-44 p-1">
          <div className="px-2.5 pb-1.5 pt-1 text-[11px] text-muted-foreground">{hint}</div>
          {/* Plain buttons (Tab navigates them) — deliberately NOT role=menu:
              a Popover has no arrow-key menu semantics, and the ARIA menu
              contract would promise navigation this doesn't implement. */}
          <div className="flex flex-col gap-0.5">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
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
                    // Arm the stamp choreography for the incoming verified
                    // state — the keyed content remounts when the status
                    // lands and plays the spring-stamp + ring.
                    if (pending === "verified") setJustStamped(true);
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
  onSearchName,
  filings = 1,
  density = "gallery",
  reason,
}: {
  startup: Startup;
  onStatusChange?: (s: Startup, choice: StatusChoice) => void;
  onDetails?: (s: Startup) => void;
  /** In-app same-name search (the ×N filings chip) — keeps SPA state. */
  onSearchName?: (name: string) => void;
  /** Same-name filings in the archive (a disambiguation directory must say so). */
  filings?: number;
  /** Visual exhibition density: 3D Gallery card vs. compact tabular Ledger row */
  density?: "gallery" | "ledger";
  /**
   * WHY this row matched, in the server's own words (`GET /api/search`,
   * F-18). Rendered verbatim — the filtering still runs client-side over the
   * cached archive (`lib/search.ts`), and this is the classification that goes
   * with it. Absent when nothing is being searched.
   */
  reason?: string;
}) {
  const dead = startup.status === "dead" || startup.status === "pivoted";
  // F-04 (frontend half): `founded` may be an RDAP domain registration or a
  // Wayback snapshot, so the label comes from `date_source` — and a null date
  // renders nothing rather than a year invented to fill the space.
  const founded = foundedShort(startup.founded, startup.date_source);
  const [expanded, setExpanded] = React.useState(false);
  const [stampChoreo, setStampChoreo] = React.useState<"verified" | "dead" | null>(null);
  const description = startup.description ?? "";
  const showToggle = description.length > 200;
  const reduce = useReducedMotion();

  const handleWrappedStatus = (s: Startup, choice: StatusChoice) => {
    if (choice === "verified") {
      setStampChoreo("verified");
    } else if (choice === "dead") {
      setStampChoreo("dead");
    }
    onStatusChange?.(s, choice);
  };

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

  // Dense Ledger Row View
  if (density === "ledger") {
    return (
      <div
        className={cn(
          "ledger-row group relative flex items-center justify-between gap-3 rounded-xl border border-border/40 bg-background/50 px-3.5 py-2.5 backdrop-blur-md",
          dead && "saturate-[0.5] opacity-80",
        )}
      >
        <StampChoreography type={stampChoreo} onComplete={() => setStampChoreo(null)} />
        <div className="flex min-w-0 items-center gap-3">
          <HueAvatar name={startup.name} size="sm" className={dead ? "grayscale" : undefined} />
          <div className="min-w-0">
            <button
              type="button"
              onClick={() => onDetails?.(startup)}
              className="truncate text-left text-xs font-bold leading-tight hover:text-primary hover:underline"
            >
              {startup.name}
            </button>
            <p className="truncate font-mono text-[10px] text-muted-foreground">
              {startup.tagline || (startup.category ? titleCase(startup.category) : "Uncategorized")}
            </p>
            {reason && (
              <p className="truncate font-mono text-[10px] text-primary/80" title={reason}>
                match: {reason}
              </p>
            )}
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2">
          {startup.category && (
            <Badge variant="secondary" className="text-[10px] py-0 px-2 font-mono">
              {titleCase(startup.category)}
            </Badge>
          )}
          {founded.text && (
            <span
              title={founded.title}
              className="font-mono text-[10px] tabular-nums text-muted-foreground"
            >
              {founded.text}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <StatusPill startup={startup} onStatusChange={handleWrappedStatus} />
          <Button
            type="button"
            variant="outline"
            size="xs"
            className="h-7 px-2 text-[11px]"
            onClick={() => onDetails?.(startup)}
          >
            Details
          </Button>
        </div>
      </div>
    );
  }

  return (
    <HolographicCard disabled={dead} className="flex h-full flex-col">
      <StampChoreography type={stampChoreo} onComplete={() => setStampChoreo(null)} />
      <motion.div
        layoutId={`startup-${startup.id}`}
        whileHover={reduce ? undefined : { y: dead ? -1 : -4, boxShadow: dead ? undefined : "0 16px 48px oklch(0.2 0.03 262 / 0.16)" }}
        whileTap={reduce ? undefined : { scale: 0.985 }}
        transition={{ type: "spring", stiffness: 380, damping: 28 }}
        className={cn(
          "glass preserve-3d relative flex h-full flex-col rounded-2xl",
          dead && "saturate-[0.6]",
        )}
      >
        {/* The FILED stamp — archival watermark over the card face */}
        {dead && (
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 -rotate-6 rounded border border-destructive/25 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-destructive/55"
          >
            Filed
          </span>
        )}
        <div className="flex h-full flex-col gap-2.5 p-4 [transform-style:preserve-3d]">
          <div className="flex items-center gap-2.5 [transform:translateZ(24px)]">
            <HueAvatar name={startup.name} className={dead ? "grayscale" : undefined} />
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
              {founded.text && <span title={founded.title}>{founded.text}</span>}
              {founded.text && startup.last_checked && <span className="text-border"> · </span>}
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

        {reason && (
          <p className="truncate font-mono text-[10px] text-primary/80" title={reason}>
            match: {reason}
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
                  : { type: "tween", ease: EASE, duration: 0.32 }
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
            <motion.div
              whileHover={reduce ? undefined : { scale: 1.06, y: -1 }}
              whileTap={reduce ? undefined : { scale: 0.95 }}
              transition={{ type: "spring", stiffness: 480, damping: 24 }}
            >
              <Badge variant="secondary" className="text-[11px]">
                {titleCase(startup.category)}
              </Badge>
            </motion.div>
          )}
          {startup.language && (
            <motion.div
              whileHover={reduce ? undefined : { scale: 1.06, y: -1 }}
              whileTap={reduce ? undefined : { scale: 0.95 }}
              transition={{ type: "spring", stiffness: 480, damping: 24 }}
            >
              <Badge variant="outline" className="text-[11px]">
                {titleCase(startup.language)}
              </Badge>
            </motion.div>
          )}
          {typeof startup.stars === "number" && startup.stars > 0 && (
            <span className="ml-auto flex items-center gap-1 font-mono text-[11px] tabular-nums text-muted-foreground">
              <Star className="h-3 w-3" /> {startup.stars.toLocaleString()}
            </span>
          )}
          {filings > 1 && (
            <button
              type="button"
              onClick={() => onSearchName?.(startup.name)}
              title={`${filings} filings share this name — check which one you mean`}
              className={cn(
                "flex items-center rounded-full border border-border/70 px-1.5 py-0.5 font-mono text-[10px] tabular-nums text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground",
                // Right-align only when the stars counter isn't already
                // claiming the row's auto margin.
                !(typeof startup.stars === "number" && startup.stars > 0) && "ml-auto",
              )}
            >
              ×{filings} filings
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-border/60 pt-3">
          {isHttpUrl(startup.website_url) && (
            <motion.div
              whileHover={reduce ? undefined : { scale: 1.04, y: -1 }}
              whileTap={reduce ? undefined : { scale: 0.96 }}
              transition={{ type: "spring", stiffness: 500, damping: 26 }}
            >
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <a
                  href={startup.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Visit ${startup.name} website (opens in a new tab)`}
                >
                  <ExternalLink className="h-3 w-3" /> Website
                </a>
              </Button>
            </motion.div>
          )}
          {isHttpUrl(startup.github_url) && (
            <motion.div
              whileHover={reduce ? undefined : { scale: 1.04, y: -1 }}
              whileTap={reduce ? undefined : { scale: 0.96 }}
              transition={{ type: "spring", stiffness: 500, damping: 26 }}
            >
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <a
                  href={startup.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View ${startup.name} source code (opens in a new tab)`}
                >
                  <FolderGit2 className="h-3 w-3" /> Code
                </a>
              </Button>
            </motion.div>
          )}
          <motion.div
            className="ml-auto"
            whileHover={reduce ? undefined : { scale: 1.04, y: -1 }}
            whileTap={reduce ? undefined : { scale: 0.96 }}
            transition={{ type: "spring", stiffness: 500, damping: 26 }}
          >
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => onDetails?.(startup)}
            >
              Details
            </Button>
          </motion.div>
        </div>
      </div>
    </motion.div>
    </HolographicCard>
  );
}

