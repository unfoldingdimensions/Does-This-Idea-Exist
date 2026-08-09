"use client";

import * as React from "react";
import { Loader2, X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { seedByGithub, seedByWebsite } from "@/lib/api";
import type { Startup } from "@/lib/types";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Add a startup — frosted glass modal (Watermelon create-community pattern,
 * adapted): animated entrance, backdrop blur, segmented source tabs.
 * Fully controlled: `open`/`onOpenChange` and `tab`/`onTabChange` live in the
 * parent, so the split-button can pick which source form to land on.
 */
export function AddStartupDialog({
  open,
  onOpenChange,
  tab,
  onTabChange,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  tab: "github" | "website";
  onTabChange: (t: "github" | "website") => void;
  onAdded: (s: Startup) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [status, setStatus] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [githubUrl, setGithubUrl] = React.useState("");
  const [websiteUrl, setWebsiteUrl] = React.useState("");
  const [nameHint, setNameHint] = React.useState("");
  const panelRef = React.useRef<HTMLDivElement>(null);
  const lastFocused = React.useRef<HTMLElement | null>(null);

  /** http(s) only — anything else would fail the backend fetch anyway. */
  const urlValid = (v: string): boolean => {
    try {
      const u = new URL(v);
      return u.protocol === "http:" || u.protocol === "https:";
    } catch {
      return false;
    }
  };

  // Focus the panel on open (Escape then works), restore focus + scroll on close.
  React.useEffect(() => {
    if (open) {
      lastFocused.current = document.activeElement as HTMLElement | null;
      document.body.style.overflow = "hidden";
      const t = setTimeout(() => panelRef.current?.focus(), 30);
      return () => {
        clearTimeout(t);
        document.body.style.overflow = "";
        lastFocused.current?.focus?.();
      };
    }
    return undefined;
  }, [open]);

  const reset = () => {
    setGithubUrl("");
    setWebsiteUrl("");
    setNameHint("");
    setStatus("");
    setError(null);
  };

  const close = () => {
    onOpenChange(false);
    reset();
  };

  const handleGithub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const url = githubUrl.trim();
    if (!url) {
      setError("Enter a GitHub repo URL first.");
      return;
    }
    if (!urlValid(url)) {
      setError("That doesn't look like a valid URL — include https://");
      return;
    }
    setError(null);
    setBusy(true);
    setStatus("Fetching repo and generating profile…");
    try {
      const entry = await seedByGithub(url);
      toast.success(`${entry.name} added`);
      onAdded(entry);
      close();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  const handleWebsite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const url = websiteUrl.trim();
    if (!url) {
      setError("Enter a website URL first.");
      return;
    }
    if (!urlValid(url)) {
      setError("That doesn't look like a valid URL — include https://");
      return;
    }
    setError(null);
    setBusy(true);
    setStatus("Fetching homepage and generating profile…");
    try {
      const entry = await seedByWebsite(url, nameHint.trim() || undefined);
      toast.success(`${entry.name} added`);
      onAdded(entry);
      close();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-4 sm:p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            onClick={close}
            aria-hidden
            className="fixed inset-0 bg-[var(--glass-overlay)] backdrop-blur-sm"
          />
          <motion.div
            ref={panelRef}
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.94, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 24 }}
            transition={{ duration: 0.4, ease: EASE }}
            onKeyDown={(e) => e.key === "Escape" && close()}
            role="dialog"
            aria-modal="true"
            aria-label="Add a startup"
            className="glass-strong relative z-10 my-auto w-full max-w-md rounded-3xl p-5 shadow-2xl outline-none sm:p-6"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-xl font-bold tracking-tight">Add a startup</h2>
                <p className="mt-1.5 max-w-[42ch] text-[13px] leading-relaxed text-muted-foreground">
                  Paste a GitHub repo or a website — the backend fetches the details and writes
                  the profile. Entries start <span className="font-medium text-foreground">unchecked</span> until
                  you review them.
                </p>
              </div>
              <button
                type="button"
                onClick={close}
                aria-label="Close"
                title="Close"
                className="flex size-8 items-center justify-center rounded-full transition-colors text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X size={18} />
              </button>
            </div>

            <Tabs
              value={tab}
              onValueChange={(v) => {
                setError(null);
                onTabChange(v as "github" | "website");
              }}
            >
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="github">GitHub link</TabsTrigger>
                <TabsTrigger value="website">Website</TabsTrigger>
              </TabsList>

              <TabsContent value="github">
                <form onSubmit={handleGithub} className="space-y-3 pt-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="gh-url">GitHub repo URL</Label>
                    <Input
                      id="gh-url"
                      placeholder="https://github.com/owner/repo"
                      value={githubUrl}
                      onChange={(e) => {
                        setGithubUrl(e.target.value);
                        setError(null);
                      }}
                      disabled={busy}
                      autoFocus
                      aria-invalid={error ? "true" : undefined}
                      aria-describedby={error ? "add-error" : undefined}
                    />
                    {error && (
                      <p id="add-error" role="alert" className="text-xs text-destructive">
                        {error}
                      </p>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Fetches name, description, created date, stars and language — then writes the
                    profile for your review.
                  </p>
                  <div className="flex justify-end pt-1">
                    <Button type="submit" disabled={busy}>
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Fetch &amp; add
                    </Button>
                  </div>
                </form>
              </TabsContent>

              <TabsContent value="website">
                <form onSubmit={handleWebsite} className="space-y-3 pt-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="ws-url">Website URL</Label>
                    <Input
                      id="ws-url"
                      placeholder="https://example.com"
                      value={websiteUrl}
                      onChange={(e) => {
                        setWebsiteUrl(e.target.value);
                        setError(null);
                      }}
                      disabled={busy}
                      aria-invalid={error ? "true" : undefined}
                      aria-describedby={error ? "add-error" : undefined}
                    />
                    {error && (
                      <p id="add-error" role="alert" className="text-xs text-destructive">
                        {error}
                      </p>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="ws-name">Name (optional)</Label>
                    <Input
                      id="ws-name"
                      placeholder="Startup name — auto-detected if empty"
                      value={nameHint}
                      onChange={(e) => setNameHint(e.target.value)}
                      disabled={busy}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Fetches the homepage, estimates the founded date (homepage → Wayback → domain
                    registration) and writes the profile.
                  </p>
                  <div className="flex justify-end pt-1">
                    <Button type="submit" disabled={busy}>
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Fetch &amp; add
                    </Button>
                  </div>
                </form>
              </TabsContent>
            </Tabs>

            {busy && <p className="pt-2 text-xs text-muted-foreground">{status}</p>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
