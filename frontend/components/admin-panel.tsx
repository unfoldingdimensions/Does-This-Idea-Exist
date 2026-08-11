"use client";

import * as React from "react";
import { AnimatePresence, motion } from "motion/react";
import { HeartPulse, Loader2, Settings2, Sprout, Stamp } from "lucide-react";
import { toast } from "sonner";
import { SPRING_SETTLE } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AdminUnauthorized,
  adminCheck,
  clearAdminToken,
  fetchSeedJobs,
  setAdminToken,
} from "@/lib/api";
import { useAdminToken } from "@/lib/use-admin-token";
import type { SeedJob } from "@/lib/types";
import { ACTIVE, SectionHeader } from "@/components/admin-shared";
import { SeedSection } from "@/components/admin-seed-section";
import { VerificationSection } from "@/components/admin-verify-section";
import { HealthCheckSection } from "@/components/admin-health-section";

export type AdminSection = "seed" | "verify" | "health";

/** Owner-only admin: vertical settings surface with three collapsible sections
 * — Seeding (serial queue + seed summary), Verification (human gate: suggested
 * queue + verify summary), Website Health Check (automated pass + buckets).
 * Seed and verify jobs run on separate workers, so a seed and a verification
 * can run at the same time; jobs persist to the jobs table and survive
 * backend restarts. */
export function AdminPanel({
  onSeeded,
  initialSection = "seed",
}: {
  onSeeded: () => void;
  initialSection?: AdminSection;
}) {
  const [open, setOpen] = React.useState(false);
  // Shared store, not local state: the header split-button and every card's
  // status pill gate on the same unlock, so they all have to see it change.
  const token = useAdminToken();
  const [tokenInput, setTokenInput] = React.useState("");
  const [unlocking, setUnlocking] = React.useState(false);
  const [unlockMsg, setUnlockMsg] = React.useState("");
  const [section, setSection] = React.useState<AdminSection | null>(initialSection);
  const [jobs, setJobs] = React.useState<SeedJob[]>([]);
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());

  const toggle = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const activeJobs = React.useMemo(
    () => jobs.filter((j) => ACTIVE.has(j.status)),
    [jobs],
  );

  const handleLocked = (msg?: string) => {
    clearAdminToken(); // notifies every subscriber, including this component
    setJobs([]);
    if (msg) setUnlockMsg(msg);
  };

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
      setUnlockMsg(err instanceof Error ? err.message : "That token didn't unlock the drawer");
    } finally {
      setUnlocking(false);
    }
  };

  // Re-attach on every open: jobs keep going server-side (seed and verify
  // workers), and reopening must show live progress + persisted history.
  // Also keep the last-known active ids so a finishing run fires onSeeded
  // exactly once.
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
        onSeeded();
        for (const j of justFinished) {
          if (j.kind === "verify") {
            toast.success(
              `Verification complete — ${j.result?.ok ?? j.ok}/${j.total} ok · ${j.failed} failed`,
            );
          } else if (j.status === "failed" || j.failed > 0) {
            toast.error(`The run finished — ${j.done} filed · ${j.failed} didn't take`, {
              description: j.errors[0] ?? "See the run summary in the panel.",
            });
          } else {
            toast.success(
              `Seed complete — ${j.ok} added · ${j.skipped} already on file`,
            );
          }
        }
      }
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        handleLocked("Session expired — re-enter your token to reopen the drawer");
        toast.error("Session expired — the drawer locked itself");
      }
    }
  }, [onSeeded]);

  React.useEffect(() => {
    // Poll while any job is active — even with the panel closed, so a finishing
    // run refreshes the archive (onSeeded) and reopen shows the result. The
    // initial refresh happens in the open/unlock handlers (not here — react-hooks
    // v7 forbids synchronous setState in effect bodies; the interval callback
    // runs async, which is allowed).
    if (!token || activeJobs.length === 0) return;
    const t = window.setInterval(() => void refreshJobs(), 2000);
    return () => window.clearInterval(t);
  }, [token, activeJobs.length, refreshJobs]);

  const sections: { key: AdminSection; icon: React.ReactNode; title: string }[] = [
    { key: "seed", icon: <Sprout className="h-4 w-4" />, title: "Seeding" },
    { key: "verify", icon: <Stamp className="h-4 w-4" />, title: "Verification" },
    { key: "health", icon: <HeartPulse className="h-4 w-4" />, title: "Website Health Check" },
  ];

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        // Re-attach on every open — the workers keep going server-side.
        if (v && token) void refreshJobs();
        if (v) setSection(initialSection);
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Admin panel"
          title="Admin — settings"
          className="h-9 w-9"
        >
          <Settings2 className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Admin — settings</DialogTitle>
          <DialogDescription>
            Seeding (one source at a time), the human verification gate, and the
            automated website health check. Seed and verify runs work in parallel;
            every run&apos;s history is kept across restarts.
          </DialogDescription>
        </DialogHeader>

        {!token ? (
          <form onSubmit={handleUnlock} className="space-y-3 pt-2">
            <div className="space-y-1.5">
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
            {unlockMsg && <p className="text-xs text-destructive">{unlockMsg}</p>}
            <Button type="submit" disabled={unlocking || !tokenInput.trim()}>
              {unlocking && <Loader2 className="h-4 w-4 animate-spin" />}
              Unlock
            </Button>
          </form>
        ) : (
          <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1 pt-2">
            {sections.map((s) => (
              <section key={s.key} className="space-y-2">
                <SectionHeader
                  icon={s.icon}
                  title={s.title}
                  open={section === s.key}
                  onToggle={() => setSection(section === s.key ? null : s.key)}
                  badge={
                    s.key === "seed" && activeJobs.some((j) => j.kind === "seed")
                      ? `${activeJobs.filter((j) => j.kind === "seed").length} active`
                      : undefined
                  }
                />
                <AnimatePresence initial={false}>
                  {section === s.key && (
                    <motion.div
                      key={s.key}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={SPRING_SETTLE}
                      className="overflow-hidden"
                    >
                      <div className="rounded-lg bg-background/60 p-3">
                        {s.key === "seed" && (
                          <SeedSection
                            jobs={jobs}
                            expanded={expanded}
                            onToggle={toggle}
                            onSeeded={() => void refreshJobs()}
                            onLocked={handleLocked}
                          />
                        )}
                        {s.key === "verify" && (
                          <VerificationSection
                            jobs={jobs}
                            expanded={expanded}
                            onToggle={toggle}
                            onSeeded={() => {
                              onSeeded();
                              void refreshJobs();
                            }}
                            onLocked={handleLocked}
                          />
                        )}
                        {s.key === "health" && (
                          <HealthCheckSection
                            expanded={expanded}
                            onToggle={toggle}
                            onSeeded={() => {
                              onSeeded();
                              void refreshJobs();
                            }}
                            onLocked={handleLocked}
                          />
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </section>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
