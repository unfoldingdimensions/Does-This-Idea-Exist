"use client";

import * as React from "react";
import {
  BadgeCheck,
  Bot,
  ExternalLink,
  FolderGit2,
  Globe,
  Info,
  Smartphone,
  TriangleAlert,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchStartupRecord } from "@/lib/api";
import { foundedLabel, formatDate, shortDate, titleCase } from "@/lib/format";
import type { EvidenceRow, Pricing, PricingPlan, StartupRecord, TeardownColumns } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The teardown dossier — one record, rendered from `GET /api/startups/{slug}`
 * (`docs/frontend-plan.md` §2.1, `docs/teardown-spec.md` §2).
 *
 * Two rules from the trust model shape every line of this file:
 *
 *  1. **A badge never sits next to a claim.** Admin Verified and Machine
 *     Verified describe the RECORD, so they render once, in their own header
 *     block, with a caption that says exactly that. Every claim instead carries
 *     its own source label — "per their pricing page · captured 15 Sep 2026".
 *  2. **No verdict, and no guessed fact.** A cell with no data reads `unknown`
 *     (never blank, never "no"), and an approximated date is labelled with the
 *     source it came from (F-04) instead of being printed as a founding year.
 *
 * Reviews are deliberately absent: they feed gap-table dimension 7 ("What their
 * users ask for"), not a panel of their own (`docs/teardown-spec.md` §9).
 */

/**
 * Mirror of the backend's `compare.slugify` (lowercase, every non-alphanumeric
 * run → a single hyphen, ends trimmed), so a shareable `/products/<slug>` link
 * can be built before the record resolves. The server's own `slug` field wins
 * as soon as it arrives — this is only here so the link is never blank.
 */
export function productSlug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

/**
 * Read a teardown column off a row the caller typed as the older flat `Startup`.
 * `GET /api/startups` returns all 40 columns (`SELECT *`), but `lib/types.ts`
 * declared only the pre-Phase-1 ones, so the extra columns are read through
 * this accessor instead of scattering unchecked casts at every use site.
 */
function col(row: object | null | undefined, key: string): string | null {
  if (!row) return null;
  const value = (row as Record<string, unknown>)[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function parseJson<T>(raw: string | null | undefined, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim());
}

/**
 * "per <source> · captured <date>", where the source is one or more clickable
 * pages. `source` columns can hold several URLs joined with " · " (the compare
 * path joins them that way), so each one gets its own link. Nothing is invented:
 * with no source and no date the line says so.
 */
function SourceLine({
  source,
  capturedAt,
  label,
  className,
}: {
  source: string | null;
  capturedAt: string | null;
  /** Fallback wording when there is a date but no source page. */
  label: string;
  className?: string;
}) {
  const urls = (source ?? "")
    .split(" · ")
    .map((s) => s.trim())
    .filter((s) => s && isHttpUrl(s));
  if (urls.length === 0 && !capturedAt) {
    return (
      <p className={cn("text-[11px] text-muted-foreground/80", className)}>
        source and capture date not recorded
      </p>
    );
  }
  return (
    <p className={cn("text-[11px] text-muted-foreground", className)}>
      per{" "}
      {urls.length > 0 ? (
        urls.map((url, i) => (
          <React.Fragment key={url}>
            {i > 0 && <span className="text-border"> · </span>}
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open the ${label} for this record — ${hostOf(url)} (opens in a new tab)`}
              className="underline underline-offset-2 hover:text-foreground"
            >
              {hostOf(url)}
            </a>
          </React.Fragment>
        ))
      ) : (
        label
      )}
      {capturedAt && <> · captured {shortDate(capturedAt)}</>}
    </p>
  );
}

/** A whole section the record has no data for. `unknown`, never blank or "no". */
function UnknownSection({ what, note }: { what: string; note: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border/60 px-3 py-2.5">
      <h4 className="ledger-header">{what}</h4>
      <p className="mt-1 flex items-start gap-1.5 text-[11px] leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 h-3 w-3 shrink-0" />
        <span>
          <span className="font-mono font-semibold">unknown</span> — {note}
        </span>
      </p>
    </div>
  );
}

/**
 * The two badges, as two visibly different signals (`docs/teardown-spec.md`
 * §8.1). Admin Verified means a human admitted the row (a funnel admission says
 * "Machine Approved" instead); Machine
 * Verified is re-earned on every weekly pass, so it is the one the reader
 * should see varying. Neither says anything about the truth of a claim.
 */
function TrustBadges({ record }: { record: StartupRecord | null }) {
  // A row can be admitted by the funnel rather than by a human. `admin_verified`
  // is already false for those, but "not admin verified" would hide WHICH gate
  // let it in - so the badge names the actual gate instead.
  const machineAdmitted = record?.approval_source === "machine";
  if (!record) {
    return (
      <div className="flex flex-wrap gap-2" aria-busy="true" aria-label="Loading trust signals">
        <span className="h-6 w-44 animate-pulse rounded-full bg-muted" />
        <span className="h-6 w-40 animate-pulse rounded-full bg-muted" />
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      <div
        className="flex flex-wrap items-center gap-2"
        title={
          machineAdmitted && record.approval_note
            ? record.approval_note
            : undefined
        }
      >
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
            record.admin_verified
              ? "border-success/25 bg-success/12 text-success dark:bg-success/15"
              : machineAdmitted
                ? "border-primary/25 bg-primary/10 text-primary"
                : "text-muted-foreground",
          )}
        >
          {machineAdmitted ? <Bot className="h-3 w-3" /> : <BadgeCheck className="h-3 w-3" />}
          {machineAdmitted ? "Machine Approved" : "Admin Verified"}
          <span className="font-mono text-[10px] font-normal opacity-80">
            {machineAdmitted
              ? `${record.approved_by ?? "funnel"} - ${
                  record.admin_verified_at
                    ? shortDate(record.admin_verified_at)
                    : "date not recorded"
                }`
              : record.admin_verified
                ? record.admin_verified_at
                  ? shortDate(record.admin_verified_at)
                  : "date not recorded"
                : "not admin verified"}
          </span>
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
            record.machine_verified
              ? "border-primary/25 bg-primary/10 text-primary"
              : "border-border/60 text-muted-foreground",
          )}
        >
          <Bot className="h-3 w-3" />
          Machine Verified
          <span className="font-mono text-[10px] font-normal opacity-80">
            {record.machine_verified
              ? `last checked ${shortDate(record.machine_verified_at)}`
              : record.machine_verified_at
                ? `lapsed — last checked ${shortDate(record.machine_verified_at)}`
                : "never checked"}
          </span>
        </span>
      </div>
      <p className="text-[10px] leading-relaxed text-muted-foreground/80">
        These two describe the <strong className="font-semibold">record</strong> — that a human
        admitted the business, and whether automation last reached the link. They say
        nothing about the truth of any claim below; each claim carries its own source instead.
      </p>
    </div>
  );
}

/** Pricing, plan by plan, each with the date it was captured (cell rule 1). */
function PricingSection({ row }: { row: object | null }) {
  const pricing = parseJson<Pricing>(col(row, "pricing_json"), {});
  const plans: PricingPlan[] = Array.isArray(pricing.plans) ? pricing.plans : [];
  const free = (pricing.free_tier ?? "").trim();
  const capturedAt = col(row, "pricing_captured_at");
  const source = col(row, "pricing_source_url");

  if (!free && plans.length === 0) {
    return (
      <UnknownSection
        what="Pricing — plan by plan"
        note="no pricing was captured for this record. Pricing decays, so it is never inferred from a similar product."
      />
    );
  }
  return (
    <div>
      <h4 className="ledger-header">Pricing — plan by plan</h4>
      <ul className="mt-1.5 space-y-1">
        {free && (
          <li className="flex flex-wrap items-baseline gap-x-2 text-xs">
            <span className="font-semibold">Free tier</span>
            <span className="text-muted-foreground">{free}</span>
          </li>
        )}
        {plans.map((plan, i) => (
          <li key={`${plan.name}-${i}`} className="flex flex-wrap items-baseline gap-x-2 text-xs">
            <span className="font-semibold">{plan.name || "unnamed plan"}</span>
            <span className="font-mono tabular-nums text-muted-foreground">{plan.price || "price not stated"}</span>
            {plan.period && <span className="text-[11px] text-muted-foreground/80">/ {plan.period}</span>}
          </li>
        ))}
      </ul>
      <SourceLine source={source} capturedAt={capturedAt} label="pricing page" className="mt-1.5" />
    </div>
  );
}

/** Features — a flat list, in the product's own terms (teardown field 2). */
function FeaturesSection({ row }: { row: object | null }) {
  const features = parseJson<unknown>(col(row, "features_json"), []);
  const list = Array.isArray(features) ? features.filter((f): f is string => typeof f === "string" && !!f.trim()) : [];
  const capturedAt = col(row, "pricing_captured_at");
  const source = col(row, "pricing_source_url") ?? col(row, "website_url");

  if (list.length === 0) {
    return (
      <UnknownSection
        what="Features"
        note="this record has no captured feature list — the capture could not read an enumerating page, or the teardown has not run yet."
      />
    );
  }
  return (
    <div>
      <h4 className="ledger-header">Features — flat list</h4>
      <ul className="mt-1.5 flex flex-wrap gap-1.5">
        {list.map((feature) => (
          <li key={feature}>
            <Badge variant="secondary" className="text-[11px] font-normal">
              {feature}
            </Badge>
          </li>
        ))}
      </ul>
      <SourceLine source={source} capturedAt={capturedAt} label="features" className="mt-1.5" />
    </div>
  );
}

/** Positioning / target user, with the page it was read from. */
function PositioningSection({ row, evidence }: { row: object | null; evidence: EvidenceRow[] }) {
  const positioning = col(row, "positioning");
  const targetUsers = col(row, "target_users");
  const posEvidence = evidence.find((e) => e.evidence_type === "positioning");
  if (!positioning && !targetUsers) {
    return (
      <UnknownSection
        what="Positioning / target user"
        note="not captured on this record — the teardown reads it from the homepage hero or meta description."
      />
    );
  }
  return (
    <div>
      <h4 className="ledger-header">Positioning / target user</h4>
      {positioning && <p className="mt-1.5 text-xs leading-relaxed">“{positioning}”</p>}
      {targetUsers && (
        <p className="mt-1 text-[11px] text-muted-foreground">
          Target user: <span className="text-foreground/80">{targetUsers}</span>
        </p>
      )}
      <SourceLine
        source={posEvidence?.source_url ?? col(row, "website_url")}
        capturedAt={posEvidence?.captured_at ?? null}
        label="positioning"
        className="mt-1.5"
      />
    </div>
  );
}

/**
 * Liveness (teardown field 5). The founder's own side has no liveness signal —
 * this only ever describes the competitor's record.
 */
function LivenessSection({ row }: { row: object | null }) {
  const status = col(row, "status") ?? "active";
  const lastChecked = col(row, "last_checked");
  const failures = Number((row as Record<string, unknown> | null)?.["check_failures"] ?? 0) || 0;
  const summary = col(row, "activity_summary");
  const dead = status === "dead" || status === "pivoted";

  return (
    <div>
      <h4 className="ledger-header">Activity / liveness</h4>
      <p className="mt-1.5 flex items-center gap-1.5 text-xs">
        <span
          aria-hidden
          className={cn(
            "size-1.5 rounded-full",
            dead ? "bg-destructive" : lastChecked ? "bg-success" : "bg-muted-foreground/60",
          )}
        />
        {dead ? (
          <span className="text-destructive">
            {status} — filed, never deleted. Checked {failures} time(s) and the link was dead each time.
          </span>
        ) : lastChecked ? (
          <span>
            alive, last checked <span className="font-mono tabular-nums">{formatDate(lastChecked)}</span>
            {failures > 0 && <span className="text-destructive"> · {failures} failed check(s)</span>}
          </span>
        ) : (
          <span className="font-mono text-muted-foreground">unknown — never checked</span>
        )}
      </p>
      {summary && <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{summary}</p>}
      <SourceLine source={col(row, "website_url")} capturedAt={lastChecked} label="liveness" className="mt-1.5" />
    </div>
  );
}

/**
 * The sourced "doesn't do" list (`docs/gap-table-format.md` §4). Every entry is
 * an observation about a page that enumerates, printed with the page it came
 * from and its capture date — never a verdict about the world. A capture that
 * could not read the page is `unknown`, which is itself useful signal.
 */
function DoesntDoSection({ evidence }: { evidence: EvidenceRow[] }) {
  const negatives = evidence.filter((e) => e.evidence_type === "negative");
  if (negatives.length === 0) {
    return (
      <UnknownSection
        what="What it doesn't do"
        note="no negative observations were captured for this record. A negative is only ever an observation about a page that enumerates, so silence here is not a claim that there is nothing to find."
      />
    );
  }
  return (
    <div>
      <h4 className="ledger-header">What it doesn&rsquo;t do — observed on the pages that enumerate</h4>
      <ul className="mt-1.5 space-y-1.5">
        {negatives.map((row) => {
          const unknown = (row.value ?? "").trim().toLowerCase() === "unknown";
          const observation = (row.value ?? "").replace(/^observed:\s*/i, "").trim();
          return (
            <li key={row.id} className="flex items-start gap-2 text-xs leading-relaxed">
              <TriangleAlert
                className={cn(
                  "mt-0.5 h-3 w-3 shrink-0",
                  unknown ? "text-muted-foreground" : "text-amber-600 dark:text-amber-400",
                )}
                aria-hidden
              />
              <span className="min-w-0">
                {unknown ? (
                  <span className="font-mono font-semibold">unknown</span>
                ) : (
                  <span className="font-medium">{row.claim ?? "(observation)"}</span>
                )}
                {!unknown && observation && (
                  <span className="text-muted-foreground"> — {observation}</span>
                )}
                {unknown && observation && (
                  <span className="text-muted-foreground"> — {observation}</span>
                )}
                <span className="text-muted-foreground">
                  {" "}
                  ·{" "}
                  <a
                    href={row.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open the page this observation came from — ${hostOf(row.source_url)} (opens in a new tab)`}
                    className="underline underline-offset-2 hover:text-foreground"
                  >
                    {hostOf(row.source_url)}
                  </a>
                  {" "}
                  (captured {shortDate(row.captured_at)})
                </span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground/80">
        Each entry is a fact about a page you can open — not a claim about what the product lacks.
      </p>
    </div>
  );
}

/** The record's own links, with the security/aria hardening from item 8.
 * Every URL passes the same http(s)-only rule as the source lines: a row
 * predating the backend's `_http_url` guard must never render a `javascript:`
 * sink, however many link columns the record carries. */
function RecordLinks({ record, name }: { record: StartupRecord | null; name: string }) {
  const links: { href: string; label: string; icon: React.ReactNode; aria: string }[] = [];
  const website = col(record, "website_url");
  const github = col(record, "github_url");
  if (website && isHttpUrl(website)) {
    links.push({
      href: website,
      label: "Website",
      icon: <Globe className="h-3 w-3" />,
      aria: `Visit ${name} website (opens in a new tab)`,
    });
  }
  if (github && isHttpUrl(github)) {
    links.push({
      href: github,
      label: "Code",
      icon: <FolderGit2 className="h-3 w-3" />,
      aria: `View ${name} source code (opens in a new tab)`,
    });
  }
  const stores: [keyof TeardownColumns, string][] = [
    ["app_store_url", "App Store"],
    ["play_store_url", "Google Play"],
  ];
  for (const [key, label] of stores) {
    const href = col(record, key);
    if (href && isHttpUrl(href)) {
      links.push({
        href,
        label,
        icon: <Smartphone className="h-3 w-3" />,
        aria: `Open the ${label} listing for ${name} (opens in a new tab)`,
      });
    }
  }
  const extras: [keyof TeardownColumns, string][] = [
    ["docs_url", "Docs"],
    ["demo_url", "Demo"],
    ["product_url", "Product page"],
  ];
  for (const [key, label] of extras) {
    const href = col(record, key);
    if (href && isHttpUrl(href)) {
      links.push({
        href,
        label,
        icon: <ExternalLink className="h-3 w-3" />,
        aria: `Open the ${label} for ${name} (opens in a new tab)`,
      });
    }
  }
  if (links.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {links.map((l) => (
        <Button key={l.href} asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
          <a href={l.href} target="_blank" rel="noopener noreferrer" aria-label={l.aria}>
            {l.icon} {l.label}
          </a>
        </Button>
      ))}
    </div>
  );
}

/**
 * The record's own identity rows — including the honest `founded` display (the
 * frontend half of F-04): an RDAP or Wayback date is labelled as the
 * approximation it is, and a missing date reads `unknown` instead of a year
 * invented to fill the space.
 */
function RecordMeta({ record, row }: { record: StartupRecord | null; row: object | null }) {
  // Every column read goes through `col(row, …)` so the panel still renders the
  // identity it already has while the record is in flight — only the fields the
  // record payload alone carries (provenance, the resolved id) wait for it.
  const founded = foundedLabel(col(row, "founded"), col(row, "date_source"));
  const rows: { term: string; value: React.ReactNode; note?: string | null }[] = [];
  if (row || record) {
    rows.push({
      term: founded.label,
      value: founded.value ? (
        <span className="font-mono tabular-nums">{formatDate(founded.value)}</span>
      ) : (
        <span className="font-mono text-muted-foreground">unknown</span>
      ),
      note: founded.note,
    });
    const category = col(row, "category");
    if (category) rows.push({ term: "Category", value: titleCase(category) });
    const entityType = record?.entity_type ?? null;
    if (entityType) rows.push({ term: "Entity", value: titleCase(entityType) });
    const stars = Number((row as Record<string, unknown> | null)?.["stars"] ?? record?.stars ?? 0) || 0;
    if (stars > 0) {
      rows.push({
        term: "Stars",
        value: <span className="font-mono tabular-nums">{stars.toLocaleString()}</span>,
      });
    }
    const language = col(row, "language");
    if (language) rows.push({ term: "Language", value: titleCase(language) });
    const source = col(row, "source");
    if (source) rows.push({ term: "Filed via", value: titleCase(source) });
    if (record?.provenance) {
      rows.push({ term: "Provenance", value: <span className="font-mono text-[11px]">{record.provenance}</span> });
    }
    if (record) {
      rows.push({
        term: "Record id",
        value: <span className="font-mono tabular-nums">{record.resolved_id}</span>,
      });
    }
  }
  if (rows.length === 0) return null;
  return (
    <dl className="divide-y divide-border/50 overflow-hidden rounded-xl border border-border/60 text-xs">
      {rows.map((r) => (
        <div key={r.term} className="px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-muted-foreground">{r.term}</dt>
            <dd className="text-right font-medium">{r.value}</dd>
          </div>
          {r.note && <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground/80">{r.note}</p>}
        </div>
      ))}
    </dl>
  );
}

export function TeardownDossier({
  reference,
  initial,
  className,
}: {
  /**
   * An archive row id, a numeric id as a string, or a name slug — the endpoint
   * accepts all three. The modal passes the clicked row's id so a same-name
   * duplicate group can never resolve to a different filing than the one the
   * reader opened; `/products/<slug>` passes the shareable slug.
   */
  reference: string;
  /** The row the caller already holds; it renders while the record — which
   * carries the badges and the evidence rows — is in flight. */
  initial?: object | null | undefined;
  className?: string;
}) {
  const [record, setRecord] = React.useState<StartupRecord | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const load = React.useCallback(() => {
    let cancelled = false;
    // Deferred to a microtask: react-hooks v7 forbids a synchronous setState in
    // an effect body, and "a read is pending" is bookkeeping rather than a
    // render dependency — the effect that calls this must not cascade.
    void Promise.resolve().then(() => {
      if (cancelled) return;
      setLoading(true);
      setError(null);
    });
    fetchStartupRecord(reference)
      .then((data) => {
        if (!cancelled) setRecord(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRecord(null);
          setError(err instanceof Error ? err.message : "Could not read this record");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reference]);

  React.useEffect(() => load(), [load]);

  const row: object | null = record ?? initial ?? null;
  const evidence = record?.evidence ?? [];

  return (
    <div className={cn("space-y-4", className)}>
      <TrustBadges record={record} />

      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive"
        >
          <span>
            The teardown could not be read — {error}. The record&rsquo;s identity below is still the
            row you opened; its badges and sourced claims are not shown rather than guessed.
          </span>
          <Button variant="outline" size="xs" onClick={() => void load()} className="h-6 gap-1 text-[10px]">
            <RefreshCw className="h-3 w-3" /> Retry
          </Button>
        </div>
      )}

      {!record && loading && (
        <p className="text-[11px] text-muted-foreground" aria-live="polite">
          Reading the teardown…
        </p>
      )}

      <PricingSection row={row} />
      <FeaturesSection row={row} />
      <PositioningSection row={row} evidence={evidence} />
      <LivenessSection row={row} />
      <DoesntDoSection evidence={evidence} />

      <div className="border-t border-border/60 pt-3">
        <RecordLinks record={record} name={record?.resolved_name ?? col(row, "name") ?? "this record"} />
        <RecordMeta record={record} row={row} />
      </div>

      {record && record.duplicate_group.length > 1 && (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          <strong className="font-semibold">Same-name filings:</strong>{" "}
          {record.duplicate_group
            .map((d) => `${d.name} (id ${d.id}${d.verified ? ", human-verified" : ""})`)
            .join(" · ")}{" "}
          — the archive admits the overlap instead of hiding it. This view resolved to id{" "}
          <span className="font-mono">{record.resolved_id}</span>.
        </p>
      )}
    </div>
  );
}
