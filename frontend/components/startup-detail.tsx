"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, ExternalLink, FolderGit2, ShieldCheck, X, Share2 } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { sound } from "@/lib/sound-engine";
import { Button } from "@/components/ui/button";
import { HueAvatar } from "@/components/hue-avatar";
import { StatusPill, type StatusChoice } from "@/components/startup-card";
import { TeardownDossier, productSlug } from "@/components/teardown-dossier";
import { titleCase } from "@/lib/format";
import type { Startup } from "@/lib/types";

import { EASE } from "@/lib/motion";

/**
 * Detail modal — the card's shared-layout expansion into the teardown dossier
 * (Watermelon expandable-profile-card pattern, adapted). Card click → the card
 * itself grows into the panel; clicking a "More like this" row morphs it into
 * the next startup's dossier. Escape / overlay-click close; focus is trapped
 * to the panel and returned to the trigger on close; reduced-motion falls
 * back to a plain fade.
 *
 * The teardown itself (`pricing plan-by-plan + capture date`, `flat features`,
 * `positioning`, the sourced "doesn't do" list, liveness, both badges) comes
 * from `TeardownDossier`, which reads `GET /api/startups/{slug}` — NOT from the
 * flat list row this component is handed. The row is passed along as the
 * `initial` render so the panel is never empty while that read is in flight.
 *
 * The modal resolves the record by **id**, not by name slug: two filings can
 * share a name (the archive admits the overlap), and a reader who clicked one
 * of them must not be shown the other.
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
  // onClose arrives as an inline lambda from the page — keyed on isOpen, the
  // effect below must NOT rerun (and tear down the scroll lock) just because
  // the callback identity changed. The keydown handler reads through the ref.
  const onCloseRef = React.useRef(onClose);
  React.useEffect(() => {
    onCloseRef.current = onClose;
  });

  const isOpen = startup !== null;

  // Open/close lifecycle, keyed on isOpen (NOT the startup identity):
  // "More like this" swaps change `startup` and must not tear down the lock,
  // restore focus to the original trigger, or restart Lenis mid-navigation.
  // Focus the panel on open; restore focus to the trigger ONLY when the modal
  // closes. Scroll-lock body while open. The keydown handler lives at document
  // level: Escape must work even after focus walks out of the panel, and Tab
  // cycles inside the panel so focus never escapes an aria-modal dialog.
  React.useEffect(() => {
    if (!isOpen || wasOpen.current) return undefined;
    wasOpen.current = true;
    lastFocused.current = document.activeElement as HTMLElement | null;
    // Scroll-lock + scrollbar-gap compensation: hiding the page scrollbar
    // widens the viewport, which re-centers the archive ~5px right. Radix
    // components compensate via react-remove-scroll; this hand-rolled lock
    // must do the same (margin-right == scrollbar width) or the layout
    // jumps on open/close. Measured: without it main shifts 59→64.
    const gap = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (gap > 0) document.body.style.marginRight = `${gap}px`;
    const t = setTimeout(() => panelRef.current?.focus(), 30);

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // A nested Radix layer (the status confirm dialog, a popover) traps
        // focus inside its portal — outside this panel. When focus isn't in
        // the panel, let that layer's own Escape handler close it instead:
        // one Escape peels exactly one layer, not both at once.
        const panel = panelRef.current;
        const active = document.activeElement;
        if (panel && active && !panel.contains(active)) return;
        e.preventDefault();
        onCloseRef.current();
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
      document.body.style.marginRight = "";
      if (wasOpen.current) {
        wasOpen.current = false;
        lastFocused.current?.focus?.();
      }
    };
  }, [isOpen]);

  // Similar-item swap: the keyed panel remounts, dropping focus to <body>.
  // Put it back inside the new panel — without touching the scroll lock.
  const startupId = startup?.id;
  React.useEffect(() => {
    if (startupId === undefined) return undefined;
    const t = setTimeout(() => {
      if (document.activeElement === document.body) panelRef.current?.focus();
    }, 30);
    return () => clearTimeout(t);
  }, [startupId]);

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
            className="glass-strong relative z-10 flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl outline-none"
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

            {/* Body — data-lenis-prevent keeps Lenis from hijacking the
                wheel here (otherwise the page behind the modal scrolls). */}
            <div data-lenis-prevent className="flex-1 space-y-4 overflow-y-auto p-5">
              {startup.description && (
                <p className="max-w-[60ch] text-[13px] leading-relaxed text-muted-foreground">
                  {startup.description}
                </p>
              )}

              {/* The quick external actions keep their own rel/aria-label (item
                  8): a screen reader has to be told these open a new tab. */}
              <div className="flex flex-wrap items-center gap-2">
                {startup.website_url && (
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
                )}
                {startup.github_url && (
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
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-8 gap-1.5 text-xs cursor-pointer"
                  onClick={() => {
                    const slug = productSlug(startup.name);
                    const url =
                      typeof window !== "undefined"
                        ? `${window.location.origin}/products/${slug}`
                        : "";
                    if (url) {
                      void navigator.clipboard.writeText(url);
                      sound.playChime();
                      toast.success("Archival link copied", {
                        description: `${startup.name} now has a stable /products/${slug} coordinate.`,
                      });
                    }
                  }}
                >
                  <Share2 className="h-3 w-3" /> Share Entity
                </Button>
                <Button asChild variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
                  <Link href={`/products/${productSlug(startup.name)}`}>
                    <ArrowUpRight className="h-3 w-3" /> Open full record
                  </Link>
                </Button>
              </div>

              {/* The teardown proper — read from the record endpoint, with the
                  list row as the initial render. */}
              <div className="border-t border-border/60 pt-4">
                <TeardownDossier reference={String(startup.id)} initial={startup} />
              </div>

              {similar.length > 0 && (
                <div className="space-y-2 border-t border-border/60 pt-4">
                  <h4 className="ledger-header pb-2">More like this — {titleCase(startup.category)}</h4>
                  <div className="space-y-1">
                    {similar.map((s, idx) => (
                      <motion.button
                        key={s.id}
                        type="button"
                        initial={reduce ? undefined : { opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.04, duration: 0.2 }}
                        onClick={() => {
                          sound.playTick();
                          onNavigate(s);
                        }}
                        className="flex w-full items-center gap-2.5 rounded-xl p-2 text-left transition-colors hover:bg-accent/60 cursor-pointer"
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
                      </motion.button>
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
