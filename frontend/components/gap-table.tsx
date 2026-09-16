"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Loader2, RefreshCw, ShieldAlert, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { shortDate } from "@/lib/format";
import { compareStartups, CompareNotConfirmed } from "@/lib/api";
import {
  isCapturePending,
  type GapBand,
  type GapRow,
  type GapTable,
} from "@/lib/types";

/**
 * The gap table (F-15) — the product, not decoration (`docs/gap-table-format.md`).
 * Facts only: every cell is sourced or marked `unknown`, and the table stops at
 * the facts. No verdict, no score, no ranking, no aggregate, and no verified
 * badge anywhere inside the table — a badge describes the record, never a claim
 * (§3, §8.1). Every non-happy answer (unconfirmed draft, capture in flight,
 * unresolved competitor) is a normal answer here and gets its own honest render
 * rather than an empty box.
 */

/** Section order is fixed by §1: the three comparison bands, then unknown, then the demand group. */
const BAND_ORDER: readonly GapBand[] = [
  "you_have_they_dont",
  "they_have_you_dont",
  "both_have",
  "unknown",
  "asked_for",
] as const;

const BAND_LABELS: Record<GapBand, string> = {
  you_have_they_dont: "You have — they don't",
  they_have_you_dont: "They have — you don't",
  both_have: "Both have (parity — no differentiation here)",
  unknown: "Unknown — missing data, not a gap",
  asked_for: "Their users ask for it",
};

const TH_CLASS =
  "border-b border-border/60 px-2 py-1.5 text-left align-bottom font-mono text-[11px] font-medium uppercase tracking-wider text-muted-foreground";

/** A scheme-less source like `noted.app/docs` (the format doc's own example) is
 * still a page the reader can open; prose like "pricing lists Free only" is not
 * a link and never becomes one. Nothing is fabricated: a token either parses as
 * an http(s) URL, or is a plausible host path, or stays plain text. */
function linkHref(token: string): string | null {
  if (/^https?:\/\//i.test(token)) {
    try {
      const u = new URL(token);
      return u.protocol === "http:" || u.protocol === "https:" ? token : null;
    } catch {
      return null;
    }
  }
  // Bare host[:port][/path] — the doc's §4 source column format.
  if (/^[a-z0-9-]+(\.[a-z0-9-]+)+(:\d+)?([/?#]\S*)?$/i.test(token)) {
    return `https://${token}`;
  }
  return null;
}

function SourceToken({ token }: { token: string }) {
  const href = linkHref(token);
  if (!href) {
    return <span className="text-muted-foreground">{token}</span>;
  }
  let host = token;
  try {
    host = new URL(href).host;
  } catch {
    /* keep the raw token as the label */
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-primary underline-offset-2 hover:underline focus-visible:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
    >
      {host}
    </a>
  );
}

/** Source column: a `" · "`-joined list of URLs, each a real link, plus the
 * capture date. A blank source is `unknown`, never silently empty. */
function SourceCell({ source, capturedAt }: { source: string; capturedAt: string }) {
  const tokens = source
    .split(" · ")
    .map((t) => t.trim())
    .filter(Boolean);
  const captured = capturedAt.trim();

  return (
    <span className="text-xs text-muted-foreground">
      {tokens.length === 0 ? (
        <span className="italic">unknown</span>
      ) : (
        tokens.map((token, i) => (
          <React.Fragment key={`${token}-${i}`}>
            {i > 0 && <span aria-hidden> · </span>}
            <SourceToken token={token} />
          </React.Fragment>
        ))
      )}
      {captured && <span className="ml-1.5 text-[11px] text-muted-foreground/80">(captured {shortDate(captured)})</span>}
    </span>
  );
}

/** A claim cell. An empty cell is the literal word `unknown` — never blank,
 * never "no" (§3.4). */
function ClaimCell({ value }: { value: string }) {
  const text = (value ?? "").trim();
  if (!text) {
    return <span className="italic text-muted-foreground">unknown</span>;
  }
  return <span className="text-foreground">{text}</span>;
}

function BandSection({
  band,
  rows,
  headingId,
}: {
  band: GapBand;
  rows: GapRow[];
  headingId: string;
}) {
  const label = BAND_LABELS[band];
  const demand = band === "asked_for";

  return (
    <section
      className={cn(
        "space-y-1.5",
        demand && "rounded-r-lg border-l-2 border-l-primary/60 bg-primary/[0.04] py-2 pl-3 pr-2",
      )}
    >
      <h3
        id={headingId}
        className={cn(
          "font-mono text-[11px] font-bold uppercase tracking-[0.14em]",
          demand ? "text-primary" : "text-muted-foreground",
        )}
      >
        {label}
      </h3>
      <div className="overflow-x-auto rounded-lg border border-border/60 bg-background/60">
        <table aria-labelledby={headingId} className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th scope="col" className={TH_CLASS}>
                Dimension
              </th>
              <th scope="col" className={TH_CLASS}>
                You
              </th>
              <th scope="col" className={TH_CLASS}>
                Competitor
              </th>
              <th scope="col" className={TH_CLASS}>
                Source
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-2 py-2 text-xs italic text-muted-foreground">
                  (none)
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={`${row.dimension}-${i}`} className="border-b border-border/50 last:border-b-0">
                  <th
                    scope="row"
                    className="px-2 py-2 text-left align-top text-xs font-medium text-foreground"
                  >
                    {row.dimension}
                  </th>
                  <td className="px-2 py-2 align-top text-xs">
                    <ClaimCell value={row.you} />
                  </td>
                  <td className="px-2 py-2 align-top text-xs">
                    <ClaimCell value={row.them} />
                  </td>
                  <td className="px-2 py-2 align-top text-xs">
                    <SourceCell source={row.source} capturedAt={row.captured_at} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LoadingState() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">Running the comparison…</span>
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
        Comparing…
      </p>
      <div className="space-y-2" aria-hidden>
        {[0, 1, 2].map((b) => (
          <div key={b} className="rounded-lg border border-border/60 bg-background/60 p-3">
            <div className="mb-2 h-3 w-40 animate-pulse rounded-full bg-foreground/8 motion-reduce:animate-none" />
            {[0, 1].map((r) => (
              <div key={r} className="flex gap-2 py-1.5">
                <div className="h-3 flex-1 animate-pulse rounded-full bg-foreground/6 motion-reduce:animate-none" />
                <div className="h-3 w-16 animate-pulse rounded-full bg-foreground/6 motion-reduce:animate-none" />
                <div className="h-3 w-16 animate-pulse rounded-full bg-foreground/6 motion-reduce:animate-none" />
                <div className="h-3 w-24 animate-pulse rounded-full bg-foreground/6 motion-reduce:animate-none" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

type Settled =
  | { kind: "ready"; table: GapTable }
  | { kind: "pending"; message: string; names: string[] }
  | { kind: "needs_confirm"; message: string }
  | { kind: "error"; message: string };

type Status = Settled | { kind: "loading" };

export function GapTablePanel({
  you,
  competitors,
  competitorNames,
  onNeedsConfirm,
}: {
  you: string;
  competitors: string[];
  competitorNames?: string[];
  onNeedsConfirm?: () => void;
}) {
  const reduce = useReducedMotion();
  const uid = React.useId();
  const [attempt, setAttempt] = React.useState(0);

  // A new array identity on every parent render must not re-fire the request,
  // so the effect keys on a stable token rebuilt from the ids rather than the
  // `competitors` array itself.
  const ref = you.trim();
  const competitorsKey = competitors.join("\u0000");
  const requestKey = `${ref}\u0001${competitorsKey}\u0001${attempt}`;

  // The result is stored WITH the inputs it belongs to, so "loading" is derived
  // during render (settled.key !== requestKey) instead of being set synchronously
  // inside the effect — no cascading render, no flash of a stale table.
  const [settled, setSettled] = React.useState<{ key: string; result: Settled } | null>(null);

  React.useEffect(() => {
    if (!ref) return; // nothing to fetch; the render below stays on the error state
    let cancelled = false;
    const key = requestKey;
    const list = competitorsKey.length === 0 ? [] : competitorsKey.split("\u0000");

    compareStartups(ref, list)
      .then((res) => {
        if (cancelled) return;
        setSettled({
          key,
          result: isCapturePending(res)
            ? {
                kind: "pending",
                message:
                  res.message ??
                  "A competitor's teardown is being captured — the table will be ready once it finishes.",
                names: res.competitors.map((c) => c.name),
              }
            : { kind: "ready", table: res },
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setSettled({
          key,
          result:
            err instanceof CompareNotConfirmed
              ? { kind: "needs_confirm", message: err.message }
              : {
                  kind: "error",
                  message: err instanceof Error ? err.message : "The comparison could not be run.",
                },
        });
      });

    return () => {
      cancelled = true;
    };
  }, [ref, competitorsKey, requestKey]);

  const retry = React.useCallback(() => setAttempt((n) => n + 1), []);

  const status: Status =
    ref.length === 0
      ? { kind: "error", message: "No founder app selected to compare." }
      : settled && settled.key === requestKey
        ? settled.result
        : { kind: "loading" };

  return (
    <div className="space-y-4" aria-busy={status.kind === "loading"}>
      {status.kind === "loading" && <LoadingState />}

      {status.kind === "needs_confirm" && (
        <div
          role="alert"
          className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4"
        >
          <div className="flex items-start gap-2">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                The draft must be confirmed first
              </p>
              <p className="text-xs text-muted-foreground">{status.message}</p>
            </div>
          </div>
          {onNeedsConfirm && (
            <Button type="button" size="sm" onClick={onNeedsConfirm}>
              Confirm the draft
            </Button>
          )}
        </div>
      )}

      {status.kind === "pending" && (
        <div
          role="status"
          aria-live="polite"
          className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4"
        >
          <div className="flex items-start gap-2">
            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary motion-reduce:animate-none" />
            <div className="space-y-1">
              <p className="text-sm text-foreground">{status.message}</p>
              {status.names.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Capturing: {status.names.join(", ")}
                </p>
              )}
            </div>
          </div>
          <Button type="button" size="sm" variant="outline" onClick={retry}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </Button>
        </div>
      )}

      {status.kind === "error" && (
        <div
          role="alert"
          className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4"
        >
          <div className="flex items-start gap-2">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <p className="text-sm text-foreground">{status.message}</p>
          </div>
          <Button type="button" size="sm" variant="outline" onClick={retry}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </Button>
        </div>
      )}

      {status.kind === "ready" &&
        (() => {
          const table = status.table;
          const names =
            competitorNames && competitorNames.length > 0
              ? competitorNames
              : table.them.map((c) => c.name);
          return (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: reduce ? 0 : 0.25 }}
              className="space-y-4"
            >
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <h2 className="font-heading text-sm font-semibold text-foreground">
                  {table.you.name}
                </h2>
                {names.length > 0 && (
                  <span className="text-xs text-muted-foreground">vs {names.join(", ")}</span>
                )}
              </div>

              {BAND_ORDER.map((band) => (
                <BandSection
                  key={band}
                  band={band}
                  rows={table.groups[band] ?? []}
                  headingId={`gap-band-${uid}-${band}`}
                />
              ))}
            </motion.div>
          );
        })()}
    </div>
  );
}
