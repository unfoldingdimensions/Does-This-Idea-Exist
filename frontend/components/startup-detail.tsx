"use client";

import * as React from "react";
import { ExternalLink, FolderGit2, ShieldCheck, X } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import { HueAvatar } from "@/components/hue-avatar";
import { StatusPill, type StatusChoice } from "@/components/startup-card";
import { formatDate, titleCase } from "@/lib/format";
import type { Startup } from "@/lib/types";

import { EASE } from "@/lib/motion";

/**
 * Detail modal — the card's shared-layout expansion into a frosted dossier
 * (Watermelon expandable-profile-card pattern, adapted). Card click → the card
 * itself grows into the panel; clicking a "More like this" row morphs it into
 * the next startup's dossier. Escape / overlay-click close; focus is trapped
 * to the panel and returned to the trigger on close; reduced-motion falls
 * back to a plain fade.
 */
export function StartupDetail({
  startup,
  startups,
  onClose,
  onNavigate,
  onStatusChange,
}: {
  startup: Startup | null;
  startups: Startup[];
  onClose: () => void;
  onNavigate: (s: Startup) => void;
  onStatusChange?: (s: Startup, choice: StatusChoice) => void;
}) {
  const reduce = useReducedMotion();
  const panelRef = React.useRef<HTMLDivElement>(null);
  const lastFocused = React.useRef<HTMLElement | null>(null);
  const wasOpen = React.useRef(false);

  // Focus the panel on open; restore focus to the trigger ONLY when the modal
  // closes (a wasOpen flag — similar-item swaps change `startup` and must not
  // yank focus out of the panel mid-navigation). Scroll-lock body while open.
  // The keydown handler lives at document level: Escape must work even after
  // focus walks out of the panel (there was no trap — see the P9 finding), and
  // Tab cycles inside the panel so focus never escapes an aria-modal dialog.
  React.useEffect(() => {
    if (startup) {
      wasOpen.current = true;
      lastFocused.current = document.activeElement as HTMLElement | null;
      document.body.style.overflow = "hidden";
      const t = setTimeout(() => panelRef.current?.focus(), 30);

      const onKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          onClose();
          return;
        }
        if (e.key !== "Tab") return;
        const panel = panelRef.current;
        if (!panel) return;
        const focusables = [...panel.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )];
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey) {
          if (active === first || !panel.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else if (active === last || !panel.contains(active)) {
          e.preventDefault();
          first.focus();
        }
      };
      document.addEventListener("keydown", onKeyDown);
      return () => {
        clearTimeout(t);
        document.removeEventListener("keydown", onKeyDown);
        document.body.style.overflow = "";
        if (wasOpen.current) {
          wasOpen.current = false;
          lastFocused.current?.focus?.();
        }
      };
    }
    return undefined;
  }, [startup, onClose]);

  const similar = React.useMemo(() => {
    if (!startup) return [];
    // "More like this" must actually be similarity, not the first four rows in
    // API order (the P9 finding: CodeCrafters → BloomTech/Brightwheel/...).
    // Score same-category filings: shared language +2, same trust state +1,
    // shared significant tagline words +1 each; stars break ties.
    const STOP = new Set([
      "with", "from", "that", "this", "your", "the", "and", "for", "you",
      "are", "not", "its", "all", "has", "have", "was", "were", "will",
      "into", "their", "they", "them", "what", "when", "where", "who",
    ]);
    const words = new Set(
      (startup.tagline ?? "")
        .toLowerCase()
        .split(/\W+/)
        .filter((w) => w.length > 3 && !STOP.has(w)),
    );
    return startups
      .filter((s) => s.category === startup.category && s.id !== startup.id)
      .map((s) => {
        let score = 0;
        if (s.language && startup.language && s.language === startup.language) score += 2;
        if (s.verified === 1 && startup.verified === 1) score += 1;
        if (s.tagline) {
          for (const w of words) {
            if (s.tagline.toLowerCase().includes(w)) score += 1;
          }
        }
        return { s, score };
      })
      .sort((a, b) => b.score - a.score || (b.s.stars ?? 0) - (a.s.stars ?? 0))
      .slice(0, 4)
      .map((x) => x.s);
  }, [startups, startup]);

  return (
    <AnimatePresence>
      {startup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={onClose}
            aria-hidden
            className="absolute inset-0 bg-[var(--glass-overlay)] backdrop-blur-md"
          />
          <motion.div
            key={startup.id}
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={`${startup.name} details`}
            layoutId={reduce ? undefined : `startup-${startup.id}`}
            initial={reduce ? { opacity: 0, scale: 0.97 } : { opacity: 0 }}
            animate={reduce ? { opacity: 1, scale: 1 } : { opacity: 1 }}
            exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.18 } }}
            transition={{ type: "tween", ease: EASE, duration: 0.35 }}
            className="glass-strong relative z-10 flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-3xl outline-none"
          >
            {/* Header */}
            <div className="flex items-start gap-3 border-b border-border/60 p-5 pr-12">
              <HueAvatar name={startup.name} size="lg" />
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-xl font-bold leading-tight tracking-tight">
                  {startup.name}
                </h2>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {startup.tagline || "No tagline yet"}
                </p>
              </div>
              <div className="absolute right-4 top-4 flex items-center gap-2">
                <StatusPill startup={startup} onStatusChange={onStatusChange} />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0"
                  onClick={onClose}
                  aria-label="Close details"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {startup.description && (
                <p className="max-w-[60ch] text-[13px] leading-relaxed text-muted-foreground">
                  {startup.description}
                </p>
              )}

              <dl className="divide-y divide-border/50 overflow-hidden rounded-xl border border-border/60 text-xs">
                {startup.founded && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Founded</dt>
                    <dd className="font-mono tabular-nums">{formatDate(startup.founded)}</dd>
                  </div>
                )}
                {typeof startup.stars === "number" && startup.stars > 0 && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Stars</dt>
                    <dd className="font-mono tabular-nums">{startup.stars.toLocaleString()}</dd>
                  </div>
                )}
                {startup.language && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Language</dt>
                    <dd className="font-mono">{titleCase(startup.language)}</dd>
                  </div>
                )}
                {startup.category && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Category</dt>
                    <dd className="font-medium">{titleCase(startup.category)}</dd>
                  </div>
                )}
                {startup.source && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Source</dt>
                    <dd className="font-medium">{titleCase(startup.source)}</dd>
                  </div>
                )}
                {startup.verified_at && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Verified</dt>
                    <dd className="font-mono tabular-nums">{formatDate(startup.verified_at)}</dd>
                  </div>
                )}
                {startup.last_checked && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Last checked</dt>
                    <dd className="font-mono tabular-nums">{formatDate(startup.last_checked)}</dd>
                  </div>
                )}
                {startup.check_failures > 0 && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <dt className="text-muted-foreground">Failed checks</dt>
                    <dd className="font-mono tabular-nums text-destructive">{startup.check_failures} / 3</dd>
                  </div>
                )}
              </dl>

              <div className="flex flex-wrap items-center gap-2">
                {startup.website_url && (
                  <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                    <a href={startup.website_url} target="_blank" rel="noreferrer" aria-label={`Visit ${startup.name} website (opens in a new tab)`}>
                      <ExternalLink className="h-3 w-3" /> Website
                    </a>
                  </Button>
                )}
                {startup.github_url && (
                  <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                    <a href={startup.github_url} target="_blank" rel="noreferrer" aria-label={`View ${startup.name} source code (opens in a new tab)`}>
                      <FolderGit2 className="h-3 w-3" /> Code
                    </a>
                  </Button>
                )}
              </div>

              {similar.length > 0 && (
                <div className="space-y-2 border-t border-border/60 pt-4">
                  <h4 className="ledger-header pb-2">More like this — {titleCase(startup.category)}</h4>
                  <div className="space-y-1">
                    {similar.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => onNavigate(s)}
                        className="flex w-full items-center gap-2.5 rounded-xl p-2 text-left transition-colors hover:bg-accent/60"
                      >
                        <HueAvatar name={s.name} size="sm" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-xs font-semibold">{s.name}</span>
                          <span className="block truncate text-[11px] text-muted-foreground">
                            {s.tagline || titleCase(s.category)}
                          </span>
                        </span>
                        {s.verified === 1 && (
                          <ShieldCheck className="h-3 w-3 shrink-0 text-success" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
