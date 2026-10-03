"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowLeft,
  Coins,
  HeartPulse,
  KeyRound,
  Loader2,
  Lock,
  Sprout,
  Stamp,
  Waypoints,
} from "lucide-react";
import { toast } from "sonner";
import { SPRING_SETTLE } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AdminUnauthorized,
  adminCheck,
  clearAdminToken,
  fetchSeedJobs,
  setAdminToken,
} from "@/lib/api";
import { useAdminToken } from "@/lib/use-admin-token";
import type { SeedJob } from "@/lib/types";
import { ACTIVE, verifyResult } from "@/components/admin-shared";
import { SeedSection } from "@/components/admin-seed-section";
import { VerificationSection } from "@/components/admin-verify-section";
import { HealthCheckSection } from "@/components/admin-health-section";
import { FunnelImportSection } from "@/components/admin-funnel-section";
import { LlmGatewaysSection, useLlmGatewayBadge } from "@/components/admin-llm-section";
import { UsageSection } from "@/components/admin-usage-section";
import { cn } from "@/lib/utils";

/**
 * The admin console — the owner-only surface as a PAGE, not a modal.
 *
 * Why this shape: the six sections hold dense content (a job list, a review
 * queue, health buckets, five gateway cards, a usage report with an editable rate
 * table). In a 2xl dialog with a 65vh scroll box, reading any of them meant
 * accordion-hopping inside a letterbox. Here the sidebar is the navigation and
 * the page column is the content, so each section gets the full width and the
 * full height.
 *
 * ROUTER-FREE ON PURPOSE: the section is a CONTROLLED prop. The route
 * (`app/admin/page.tsx`) owns the URL (`?section=usage`), which keeps this
 * component mountable in a plain jsdom test — no Next router needed to prove the
 * navigation, the badges, or the unlock flow.
 *
 * ONE SECTION AT A TIME, still: each section polls, fetches and holds state, so
 * mounting all six would multiply every request by six and rebuild the original
 * problem in another shape. The sidebar carries the badges that used to justify
 * the accordion — a badge is how a section is noticed without being open.
 */

export type AdminSection = "seed" | "verify" | "funnel" | "health" | "llm" | "usage";

export const ADMIN_SECTIONS: {
  key: AdminSection;
  icon: React.ReactNode;
  title: string;
  blurb: string;
}[] = [
  {
    key: "seed",
    icon: <Sprout className="h-4 w-4" />,
    title: "Seeding",
    blurb: "One source at a time; every run's history is kept.",
  },
  {
    key: "verify",
    icon: <Stamp className="h-4 w-4" />,
    title: "Verification",
    blurb: "The human gate: review the suggested queue and stamp.",
  },
  {
    key: "funnel",
    icon: <Waypoints className="h-4 w-4" />,
    title: "Funnel import",
    blurb: "Apply a completed liveness-funnel run (dry-run first).",
  },
  {
    key: "health",
    icon: <HeartPulse className="h-4 w-4" />,
    title: "Website Health Check",
    blurb: "The automated pass, its buckets and re-checks.",
  },
  {
    key: "llm",
    icon: <KeyRound className="h-4 w-4" />,
    title: "LLM gateways",
    blurb: "Which provider every seed and capture calls, and its key.",
  },
  {
    key: "usage",
    icon: <Coins className="h-4 w-4" />,
    title: "Usage",
    blurb: "What the calls cost, the rate table, and the spend brake.",
  },
];

const SECTION_KEYS = ADMIN_SECTIONS.map((s) => s.key);

/** Is this string one of ours? Used by the route to fall back instead of blanking. */
export function isAdminSection(value: string | null | undefined): value is AdminSection {
  return typeof value === "string" && (SECTION_KEYS as string[]).includes(value);
}

export function AdminConsole({
  section,
  onSectionChange,
}: {
  section: AdminSection;
  onSectionChange: (next: AdminSection) => void;
}) {
  // Shared store, not local state: the archive page's own controls gate on the
  // same unlock, so they all have to see it change.
  const token = useAdminToken();
  const [tokenInput, setTokenInput] = React.useState("");
  const [unlocking, setUnlocking] = React.useState(false);
  const [unlockMsg, setUnlockMsg] = React.useState("");
  const [jobs, setJobs] = React.useState<SeedJob[]>([]);
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());
  // Badge for the LLM section: "needs a key" while the ACTIVE gateway cannot be
  // switched to. Fetched once per unlock (the section would only know it after
  // being opened), then kept current by the section itself.
  const llmBadge = useLlmGatewayBadge(Boolean(token));
  // Parked batches come from the SAME job list the seed section renders — no
  // second source of truth, and the badge is how a parked batch is noticed
  // without opening the section.
  const parkedCount = jobs.filter((j) => j.status === "paused").length;

  const toggle = React.useCallback(
    (key: string) =>
      setExpanded((prev) => {
        const next = new Set(prev);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return next;
      }),
    [],
  );

  const activeJobs = React.useMemo(() => jobs.filter((j) => ACTIVE.has(j.status)), [jobs]);

  const handleLocked = React.useCallback((msg?: string) => {
    clearAdminToken(); // notifies every subscriber, including this component
    setJobs([]);
    if (msg) setUnlockMsg(msg);
  }, []);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim() || unlocking) return;
    setUnlocking(true);
    setUnlockMsg("");
    try {
      await adminCheck(tokenInput.trim());
      setAdminToken(tokenInput.trim());
      setTokenInput("");
      void refreshJobs();
    } catch (err) {
      setUnlockMsg(err instanceof Error ? err.message : "That token didn't unlock the console");
    } finally {
      setUnlocking(false);
    }
  };

  const handleLock = () => {
    clearAdminToken();
    setJobs([]);
    setUnlockMsg("");
    toast.success("Locked — the admin console is read-only until you re-enter the token");
  };

  // Jobs keep going server-side (seed, verify and capture workers), so the
  // console attaches a poll while anything is active and keeps the last-known
  // active ids so a finishing run toasts exactly once.
  const lastActiveIds = React.useRef<Set<string>>(new Set());
  const refreshJobs = React.useCallback(async () => {
    try {
      const list = await fetchSeedJobs();
      setJobs(list);
      const nowActive = new Set(
        list.filter((j) => ACTIVE.has(j.status)).map((j) => j.id),
      );
      const justFinished = list.filter(
        (j) =>
          lastActiveIds.current.has(j.id) &&
          !ACTIVE.has(j.status) &&
          !nowActive.has(j.id),
      );
      lastActiveIds.current = nowActive;
      if (justFinished.length > 0) {
        for (const j of justFinished) {
          if (j.kind === "verify") {
            toast.success(
              `Verification complete — ${verifyResult(j)?.ok ?? j.ok}/${j.total} ok · ${j.failed} failed`,
            );
          } else if (j.status === "failed" || j.failed > 0) {
            toast.error(`The run finished — ${j.done} filed · ${j.failed} didn't take`, {
              description: j.errors[0] ?? "See the run summary in the console.",
            });
          } else {
            toast.success(`Seed complete — ${j.ok} added · ${j.skipped} already on file`);
          }
        }
      }
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        handleLocked("Session expired — re-enter your token to reopen the console");
        toast.error("Session expired — the console locked itself");
      }
    }
  }, [handleLocked]);

  // Stable identities for the section children: inline lambdas here changed on
  // every render, which recreated HealthCheckSection's `poll` and tore down and
  // re-ran its effects (and the polling interval above) mid-flight.
  const refreshOnly = React.useCallback(() => void refreshJobs(), [refreshJobs]);

  React.useEffect(() => {
    // Poll while any job is active. The archive page refetches on its own mount,
    // so a finished run needs no cross-page callback — only its toast.
    if (!token || activeJobs.length === 0) return;
    const t = window.setInterval(() => void refreshJobs(), 2000);
    return () => window.clearInterval(t);
  }, [token, activeJobs.length, refreshJobs]);

  // First paint after unlock: the interval callback runs async. Deferred because
  // react-hooks v7 forbids synchronous setState in an effect body.
  React.useEffect(() => {
    if (!token) return;
    const t = window.setTimeout(() => void refreshJobs(), 0);
    return () => window.clearTimeout(t);
  }, [token, refreshJobs]);

  const badgeFor = (key: AdminSection): string | undefined => {
    if (key === "seed") {
      const active = activeJobs.filter((j) => j.kind === "seed").length;
      return active > 0 ? `${active} active` : undefined;
    }
    if (key === "llm") return llmBadge ?? undefined;
    if (key === "usage" && parkedCount > 0) return `${parkedCount} parked`;
    return undefined;
  };

  const active = ADMIN_SECTIONS.find((s) => s.key === section) ?? ADMIN_SECTIONS[0];

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-8 pb-16 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
            Owner-only
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Admin — settings</h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
            Seeding, the human verification gate, the funnel import, the automated website health
            check, the LLM gateways, and what the calls cost. Seed and verify runs work in parallel;
            every run&apos;s history is kept across restarts.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {token && (
            <Button variant="ghost" size="sm" onClick={handleLock} title="Forget the token">
              <Lock className="h-3.5 w-3.5" />
              <span className="ml-1 text-xs">Lock</span>
            </Button>
          )}
          <Button variant="ghost" size="sm" asChild>
            <Link href="/" className="inline-flex items-center">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span className="ml-1 text-xs">Back to the archive</span>
            </Link>
          </Button>
        </div>
      </header>

      {!token ? (
        <form
          onSubmit={handleUnlock}
          className="mt-8 max-w-md rounded-xl border border-border/60 bg-card/60 p-5"
        >
          <h2 className="text-sm font-medium">Unlock</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            The console reads and writes the owner-only endpoints, so it stays locked until you
            paste your admin token. It is the <code className="font-mono">ADMIN_TOKEN</code> in{" "}
            <code className="font-mono">backend/.env</code>, and it is kept in this tab&apos;s
            session storage only.
          </p>
          <div className="mt-4 space-y-1.5">
            <Label htmlFor="admin-token">Admin token</Label>
            <Input
              id="admin-token"
              type="password"
              placeholder="Your owner token"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              disabled={unlocking}
              autoFocus
            />
          </div>
          {unlockMsg && <p className="mt-2 text-xs text-destructive">{unlockMsg}</p>}
          <Button type="submit" className="mt-4" disabled={unlocking || !tokenInput.trim()}>
            {unlocking && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
            Unlock
          </Button>
        </form>
      ) : (
        <div className="mt-7 flex flex-col gap-6 md:flex-row md:gap-8">
          {/* The navigation. Below md it scrolls horizontally under the header —
              a burger would hide the one thing this change exists to surface. */}
          <nav
            aria-label="Admin sections"
            className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-2 md:mx-0 md:w-60 md:shrink-0 md:flex-col md:overflow-visible md:px-0 md:pb-0 md:sticky md:top-6 md:self-start"
          >
            {ADMIN_SECTIONS.map((s) => {
              const on = s.key === section;
              const badge = badgeFor(s.key);
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => onSectionChange(s.key)}
                  aria-current={on ? "page" : undefined}
                  className={cn(
                    "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors md:w-full",
                    on
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                  )}
                >
                  <span className={cn("shrink-0", on && "text-primary")}>{s.icon}</span>
                  <span className="font-medium whitespace-nowrap">{s.title}</span>
                  {badge && (
                    <span className="ml-auto shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
                      {badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="min-w-0 flex-1">
            <div className="mb-3">
              <h2 className="text-lg font-medium">{active.title}</h2>
              <p className="text-xs text-muted-foreground">{active.blurb}</p>
            </div>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={section}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={SPRING_SETTLE}
                className="rounded-xl border border-border/60 bg-card/60 p-4"
              >
                {section === "seed" && (
                  <SeedSection
                    jobs={jobs}
                    expanded={expanded}
                    onToggle={toggle}
                    onSeeded={refreshOnly}
                    onLocked={handleLocked}
                  />
                )}
                {section === "verify" && (
                  <VerificationSection
                    jobs={jobs}
                    expanded={expanded}
                    onToggle={toggle}
                    onSeeded={refreshOnly}
                    onLocked={handleLocked}
                  />
                )}
                {section === "funnel" && (
                  <FunnelImportSection onSeeded={refreshOnly} onLocked={handleLocked} />
                )}
                {section === "health" && (
                  <HealthCheckSection
                    expanded={expanded}
                    onToggle={toggle}
                    onSeeded={refreshOnly}
                    onLocked={handleLocked}
                  />
                )}
                {section === "llm" && <LlmGatewaysSection onLocked={handleLocked} />}
                {section === "usage" && <UsageSection onLocked={handleLocked} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}
