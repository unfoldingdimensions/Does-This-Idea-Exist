"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Archive, GitCompare, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TeardownDossier } from "@/components/teardown-dossier";
import { FounderAppDialog } from "@/components/founder-app-dialog";
import { GapTablePanel } from "@/components/gap-table";
import { GapExportButtons } from "@/components/gap-export-buttons";
import { RecordNotFound, fetchStartupRecord, getFounderApp } from "@/lib/api";
import { foundedShort, titleCase } from "@/lib/format";
import type { FounderAppDraft, StartupRecord } from "@/lib/types";

/**
 * `/products/<slug>` — the stable per-product address (F-17).
 *
 * Until now the only way to point at a filing was `/?q=<name>`, which is not a
 * coordinate: it re-runs a fuzzy search and can land on a different row of a
 * same-name duplicate group. "Share Entity" now copies this URL instead, and
 * this page resolves the slug through `GET /api/startups/{slug}`, whose
 * collision rule (human-verified first, then the lowest id) is the same one the
 * comparison uses — so a shared link and a comparison agree on which filing
 * they mean.
 *
 * It is also the founder's entry point: "Compare with my app" opens the
 * three-path ingest dialog, and the gap table only appears once the draft has
 * been confirmed (confirm-before-diff, `docs/teardown-spec.md` §3).
 */
export default function ProductPage() {
  const params = useParams();
  const raw = params?.slug;
  const slug = typeof raw === "string" ? raw : Array.isArray(raw) ? (raw[0] ?? "") : "";

  const [record, setRecord] = React.useState<StartupRecord | null>(null);
  const [status, setStatus] = React.useState<"loading" | "ready" | "missing" | "error">("loading");
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [draft, setDraft] = React.useState<FounderAppDraft | null>(null);
  // `?you=<founder app id>` re-opens a comparison by link, so a founder who
  // closes the laptop mid-comparison does not have to re-enter their app from
  // scratch. It is also what makes the comparison shareable between the two of
  // them. An id that is not confirmed simply reaches the gap table's own
  // "confirm the draft first" state — the refusal is never hidden here.
  const search = useSearchParams();
  const youParam = search.get("you");

  const load = React.useCallback(() => {
    let cancelled = false;
    // The whole read runs on a microtask: react-hooks v7 forbids a synchronous
    // setState in an effect body, and "a read is pending" is bookkeeping rather
    // than a render dependency. The effect that calls this must not cascade.
    void Promise.resolve().then(() => {
      if (cancelled) return;
      if (!slug) {
        setStatus("missing");
        return;
      }
      setStatus("loading");
      setError(null);
      return fetchStartupRecord(slug)
        .then((r) => {
          if (cancelled) return;
          setRecord(r);
          setStatus("ready");
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setRecord(null);
          if (err instanceof RecordNotFound) {
            setStatus("missing");
          } else {
            setError(err instanceof Error ? err.message : "The archive could not be read");
            setStatus("error");
          }
        });
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  React.useEffect(() => load(), [load]);

  React.useEffect(() => {
    const id = Number.parseInt(youParam ?? "", 10);
    if (!Number.isFinite(id) || id <= 0) return undefined;
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (cancelled) return;
      return getFounderApp(id)
        .then((detail) => {
          if (!cancelled) setDraft(detail);
        })
        .catch(() => {
          // A stale link is not an error page: the founder simply starts a new
          // draft, and the button below is the way in.
        });
    });
    return () => {
      cancelled = true;
    };
  }, [youParam]);

  if (status === "loading") {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-20 pt-10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          <Loader2 className="h-4 w-4 animate-spin" /> Reading the archive…
        </div>
      </main>
    );
  }

  if (status === "missing") {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-4 pb-20 pt-24 text-center">
        <div className="glass max-w-md rounded-3xl px-8 py-12">
          <Archive className="mx-auto h-8 w-8 text-muted-foreground" />
          <h1 className="mt-4 font-display text-3xl font-bold tracking-tight">Not filed</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Nothing in the archive matches{" "}
            <span className="font-mono text-foreground/80">{slug}</span>. It was never filed, or the
            slug is not one this archive knows.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex h-9 items-center gap-1.5 rounded-full bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Back to the archive
          </Link>
        </div>
      </main>
    );
  }

  if (status === "error" || !record) {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-20 pt-10">
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs text-destructive"
        >
          <span>
            The archive could not be read{error ? ` — ${error}` : ""}. This is a connection problem,
            not a missing filing.
          </span>
          <Button variant="outline" size="sm" onClick={() => void load()} className="h-7 gap-1.5 text-[11px]">
            <RefreshCw className="h-3 w-3" /> Retry
          </Button>
        </div>
      </main>
    );
  }

  const founded = foundedShort(record.founded, record.date_source);

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-24 pt-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to the archive
      </Link>

      <header className="mt-5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="font-display text-3xl font-bold tracking-tight">{record.resolved_name}</h1>
          {record.category && (
            <Badge variant="secondary" className="text-[11px]">
              {titleCase(record.category)}
            </Badge>
          )}
        </div>
        {record.tagline && (
          <p className="mt-1 text-sm text-muted-foreground">{record.tagline}</p>
        )}
        <p className="mt-2 font-mono text-[10px] text-muted-foreground">
          /products/{record.slug}
          {founded.text && (
            <>
              {" · "}
              <span title={founded.title}>{founded.text}</span>
            </>
          )}
        </p>
      </header>

      <section className="mt-6" aria-label="Teardown dossier">
        <TeardownDossier reference={slug} initial={record} />
      </section>

      {/* The founder's side. The gap table cannot render before the draft is
          confirmed, and the export buttons only appear once it exists. */}
      <section className="mt-8 border-t border-border/60 pt-6" aria-label="Compare with your app">
        <h2 className="ledger-header">Compare with your app</h2>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
          Describe your app — by URL, by form, or by pasting a payload your own agent produced — then
          review and confirm the draft. The gap table only runs against a draft you have confirmed.
          Reopening this link with <span className="font-mono">?you=&lt;id&gt;</span> resumes the
          comparison.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="sm" className="h-8 gap-1.5 text-xs" onClick={() => setDialogOpen(true)}>
            <GitCompare className="h-3 w-3" />
            {draft ? "Edit my app" : "Compare with my app"}
          </Button>
          {draft && (
            <span className="font-mono text-[10px] text-muted-foreground">
              your app: {draft.profile?.name || `founder app ${draft.founder_app_id}`} · status{" "}
              {draft.archive_status}
            </span>
          )}
        </div>

        {draft && (
          <div className="mt-4 space-y-4">
            <GapTablePanel
              you={String(draft.founder_app_id)}
              competitors={[slug]}
              competitorNames={[record.resolved_name]}
              onNeedsConfirm={() => {
                setDraft(null);
                setDialogOpen(true);
              }}
            />
            {/* Exports only once the draft is confirmed: `/api/export` enforces the
                same confirm-before-diff gate as the table, so offering the three
                buttons to an unconfirmed draft would be offering three actions
                that cannot succeed. */}
            {draft.confirmed && (
              <GapExportButtons you={String(draft.founder_app_id)} competitors={[slug]} />
            )}
          </div>
        )}
      </section>

      <FounderAppDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCommitted={(committed) => setDraft(committed)}
      />
    </main>
  );
}
