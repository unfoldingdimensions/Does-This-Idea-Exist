"use client";

import * as React from "react";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { seedByGithub, seedByWebsite } from "@/lib/api";
import type { Startup } from "@/lib/types";

export function AddStartupDialog({ onAdded }: { onAdded: (s: Startup) => void }) {
  const [open, setOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [status, setStatus] = React.useState("");
  const [githubUrl, setGithubUrl] = React.useState("");
  const [websiteUrl, setWebsiteUrl] = React.useState("");
  const [nameHint, setNameHint] = React.useState("");

  const reset = () => {
    setGithubUrl("");
    setWebsiteUrl("");
    setNameHint("");
    setStatus("");
  };

  const handleGithub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUrl.trim() || busy) return;
    setBusy(true);
    setStatus("Fetching repo and generating profile…");
    try {
      const entry = await seedByGithub(githubUrl.trim());
      toast.success(`${entry.name} added`);
      onAdded(entry);
      setOpen(false);
      reset();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  const handleWebsite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!websiteUrl.trim() || busy) return;
    setBusy(true);
    setStatus("Fetching homepage and generating profile…");
    try {
      const entry = await seedByWebsite(websiteUrl.trim(), nameHint.trim() || undefined);
      toast.success(`${entry.name} added`);
      onAdded(entry);
      setOpen(false);
      reset();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" /> Add startup
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add a startup</DialogTitle>
          <DialogDescription>
            Paste a GitHub repo or a website — the backend fetches the details and writes the
            profile. Entries start as <span className="font-medium">unchecked</span> until you review them.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="github">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="github">GitHub link</TabsTrigger>
            <TabsTrigger value="website">Website</TabsTrigger>
          </TabsList>

          <TabsContent value="github">
            <form onSubmit={handleGithub} className="space-y-3 pt-2">
              <div className="space-y-1.5">
                <Label htmlFor="gh-url">GitHub repo URL</Label>
                <Input
                  id="gh-url"
                  placeholder="https://github.com/owner/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  disabled={busy}
                  autoFocus
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Fetches name, description, created date, stars and language — then writes the
                profile via deepseek-v4-flash.
              </p>
              <DialogFooter>
                <Button type="submit" disabled={busy || !githubUrl.trim()}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Fetch &amp; add
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <TabsContent value="website">
            <form onSubmit={handleWebsite} className="space-y-3 pt-2">
              <div className="space-y-1.5">
                <Label htmlFor="ws-url">Website URL</Label>
                <Input
                  id="ws-url"
                  placeholder="https://example.com"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  disabled={busy}
                />
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
              <DialogFooter>
                <Button type="submit" disabled={busy || !websiteUrl.trim()}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Fetch &amp; add
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>

        {busy && <p className="text-xs text-muted-foreground">{status}</p>}
      </DialogContent>
    </Dialog>
  );
}
