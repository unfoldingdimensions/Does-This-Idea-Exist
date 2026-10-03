"use client";

import * as React from "react";
import {
  CircleAlert,
  CircleCheck,
  Coins,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Save,
  Square,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AdminUnauthorized,
  cancelSeed,
  clearLlmRates,
  fetchLlmUsage,
  resumeSeed,
  saveLlmRates,
  setLlmBudget,
} from "@/lib/api";
import type {
  ParkedJob,
  RateRow,
  SpendWindow,
  UsageReport,
} from "@/lib/types";
import { money, parkedReason } from "@/components/admin-shared";
import { cn } from "@/lib/utils";

/**
 * Usage — the §7.4 spend surface: what the LLM calls cost, where the number comes
 * from, and the two controls over it (the per-batch budget and the rate table).
 *
 * The rule this screen exists to keep: a $ is never shown without saying whether
 * it is the WHOLE bill. `cost_complete: false` means some calls had no price, so
 * the figure is a floor — the panel says so instead of letting a partial sum pass
 * for a total, and an unknown price renders as "unknown", never as $0.00.
 */

const WINDOW_LABELS: Record<"today" | "week" | "all", string> = {
  today: "Today",
  week: "Last 7 days",
  all: "All time",
};

function failureText(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

/** "1,234" — token counts are read, not compared, so group them. */
function num(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString() : "unknown";
}

function SpendTile({ label, window }: { label: string; window?: SpendWindow }) {
  if (!window) {
    return (
      <div className="rounded-lg bg-muted/40 p-3">
        <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="mt-1 text-lg font-semibold tabular-nums text-muted-foreground">unknown</p>
        <p className="text-xs text-muted-foreground">the ledger could not be read</p>
      </div>
    );
  }
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{money(window.cost_usd)}</p>
      <p className="text-xs text-muted-foreground">
        {window.attempts} {window.attempts === 1 ? "call" : "calls"} · {num(window.total_tokens)} tokens
      </p>
      {!window.cost_complete && window.attempts > 0 && (
        <p className="mt-0.5 text-xs text-amber-600 dark:text-amber-500">
          a floor — {window.unpriced_attempts} unpriced
        </p>
      )}
      {window.usage_missing_share !== null && window.usage_missing_share > 0 && (
        <p className="mt-0.5 text-xs text-muted-foreground">
          {Math.round(window.usage_missing_share * 100)}% of calls sent no usage block
        </p>
      )}
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "warn" }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-0.5 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("tabular-nums", tone === "warn" && "text-amber-600 dark:text-amber-500")}>
        {value}
      </span>
    </div>
  );
}

/** One editable rate row: three prices, plus where the numbers came from. */
function RateEditorRow({
  model,
  row,
  draft,
  onChange,
}: {
  model: string;
  row: RateRow;
  draft: { input: string; output: string; cached_input: string };
  onChange: (model: string, field: "input" | "output" | "cached_input", value: string) => void;
}) {
  const unpriced = row.input === null && row.output === null;
  return (
    <div className="rounded-lg bg-muted/40 p-2">
      <div className="flex flex-wrap items-center justify-between gap-x-2">
        <span className="font-mono text-xs font-medium">{model}</span>
        <span className="text-[11px] text-muted-foreground">
          {row.verified ? "verified" : "unverified"} · {row.as_of ?? "no date"}
          {row.source ? ` · ${row.source.replace(/^https?:\/\//, "").slice(0, 40)}` : ""}
        </span>
      </div>
      <div className="mt-1.5 grid grid-cols-3 gap-2">
        {(["input", "output", "cached_input"] as const).map((field) => (
          <label key={field} className="space-y-0.5">
            <span className="block text-[11px] uppercase tracking-wider text-muted-foreground">
              {field === "cached_input" ? "cached read" : field}
            </span>
            <Input
              value={draft[field]}
              onChange={(e) => onChange(model, field, e.target.value)}
              inputMode="decimal"
              placeholder="—"
              className="h-7 text-xs tabular-nums"
            />
          </label>
        ))}
      </div>
      {unpriced && (
        <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-500">
          no prices: calls on this model are recorded unpriced {row.notes ? `— ${row.notes}` : ""}
        </p>
      )}
    </div>
  );
}

export function UsageSection({ onLocked }: { onLocked: (msg?: string) => void }) {
  const [report, setReport] = React.useState<UsageReport | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [budgetDraft, setBudgetDraft] = React.useState("");
  const [resumeDraft, setResumeDraft] = React.useState<Record<string, string>>({});
  const [ratesDraft, setRatesDraft] = React.useState<
    Record<string, { input: string; output: string; cached_input: string }>
  >({});
  const [ratesDirty, setRatesDirty] = React.useState(false);
  const aliveRef = React.useRef(true);

  React.useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  const seedDrafts = React.useCallback((next: UsageReport) => {
    // Only ever seeds UNTOUCHED fields: a background refresh must not wipe what
    // the operator is part-way through typing.
    setRatesDraft((prev) => {
      if (Object.keys(prev).length > 0) return prev;
      const draft: Record<string, { input: string; output: string; cached_input: string }> = {};
      for (const [model, row] of Object.entries(next.rates.models)) {
        draft[model] = {
          input: row.input === null ? "" : String(row.input),
          output: row.output === null ? "" : String(row.output),
          cached_input: row.cached_input === null ? "" : String(row.cached_input),
        };
      }
      return draft;
    });
    setBudgetDraft((prev) =>
      prev === "" && next.budget.budget_usd !== null ? String(next.budget.budget_usd) : prev,
    );
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchLlmUsage();
      if (!aliveRef.current) return;
      setReport(next);
      setLoadError(null);
      seedDrafts(next);
    } catch (err) {
      if (!aliveRef.current) return;
      if (err instanceof AdminUnauthorized) {
        const locked = "Admin session expired — re-enter your token";
        setLoadError(locked);
        onLocked(locked);
        return;
      }
      const msg = failureText(err, "Couldn't read the usage ledger");
      setLoadError(msg);
      toast.error("Couldn't read the usage ledger", { description: msg });
    } finally {
      if (aliveRef.current) setLoading(false);
    }
  }, [onLocked, seedDrafts]);

  React.useEffect(() => {
    // Deferred: react-hooks v7 forbids synchronous setState in an effect body
    // (same pattern as the gateway and verification sections).
    const t = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(t);
  }, [load]);

  /** Every action goes through here: one busy key, one reload, one error path. */
  const act = React.useCallback(
    async (key: string, fn: () => Promise<unknown>, ok: string) => {
      setBusy(key);
      try {
        const result = await fn();
        if (!aliveRef.current) return;
        const detail =
          result && typeof result === "object" && "message" in result
            ? String((result as { message?: string }).message ?? "")
            : "";
        toast.success(ok, detail ? { description: detail } : undefined);
        await load();
        setRatesDirty(false);
      } catch (err) {
        if (!aliveRef.current) return;
        if (err instanceof AdminUnauthorized) {
          onLocked("Admin session expired — re-enter your token");
          return;
        }
        toast.error("That didn't take", { description: failureText(err, "Unknown error") });
      } finally {
        if (aliveRef.current) setBusy(null);
      }
    },
    [load, onLocked],
  );

  const saveRates = () =>
    act(
      "rates",
      () => {
        const payload: Record<string, Partial<RateRow>> = {};
        for (const [model, row] of Object.entries(report?.rates.models ?? {})) {
          const draft = ratesDraft[model];
          // An empty field is a deliberate "no price" (null), never 0 — a blank
          // rate must not turn into a free model.
          const parse = (raw: string): number | null => {
            const trimmed = raw.trim();
            if (trimmed === "") return null;
            const value = Number(trimmed);
            return Number.isFinite(value) && value >= 0 ? value : null;
          };
          payload[model] = {
            input: draft ? parse(draft.input) : row.input,
            output: draft ? parse(draft.output) : row.output,
            cached_input: draft ? parse(draft.cached_input) : row.cached_input,
            cached_write: row.cached_write,
            source: row.source,
            as_of: row.as_of,
            notes: row.notes,
            verified: row.verified,
          };
        }
        return saveLlmRates(payload);
      },
      "Rate table saved",
    );

  const budgetStatus = report?.budget;
  const parked: ParkedJob[] = report?.parked ?? [];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Every LLM call this install makes is recorded, priced and attributed to the
          batch that made it. Prices are list prices, not an invoice.
        </p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void load()}
          disabled={loading}
          className="shrink-0"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          <span className="ml-1 text-xs">Refresh</span>
        </Button>
      </div>

      {loadError && (
        <div className="flex items-start gap-2 rounded-lg bg-destructive/10 p-2 text-xs text-destructive">
          <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{loadError}</span>
        </div>
      )}

      {/* The ledger itself: the state the panel must not paper over. */}
      {report && (report.ledger_error || !report.ledger_present) && (
        <div className="flex items-start gap-2 rounded-lg bg-amber-500/10 p-2 text-xs text-amber-700 dark:text-amber-400">
          <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            <strong>Nothing below is a measurement yet.</strong>{" "}
            {report.ledger_error
              ? `The spend ledger could not be read (${report.ledger_error}).`
              : "The spend ledger table does not exist yet."}{" "}
            It is created the first time the backend starts after metering shipped, so a
            restart of the API is enough.
          </span>
        </div>
      )}

      {/* Parked batches: the reason this surface has buttons. */}
      {parked.map((job) => (
        <div key={job.id} className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
          <div className="flex items-start gap-2">
            <Square className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium">
                A {job.kind} batch is parked · {job.ok} filed, {job.done}/{job.total} done
              </p>
              <p className="text-xs text-muted-foreground">{parkedReason(job as never)}</p>
              <p className="text-xs text-muted-foreground">
                Everything it wrote was kept. Resuming continues where it stopped and skips
                what it already handled — nothing is re-paid for.
              </p>
              <div className="mt-2 flex flex-wrap items-end gap-2">
                <label className="space-y-0.5">
                  <span className="block text-[11px] uppercase tracking-wider text-muted-foreground">
                    new budget (USD, blank = keep)
                  </span>
                  <Input
                    value={resumeDraft[job.id] ?? ""}
                    onChange={(e) =>
                      setResumeDraft((prev) => ({ ...prev, [job.id]: e.target.value }))
                    }
                    inputMode="decimal"
                    placeholder="unlimited"
                    className="h-7 w-32 text-xs tabular-nums"
                  />
                </label>
                <Button
                  size="sm"
                  disabled={busy !== null}
                  onClick={() =>
                    act(
                      `resume:${job.id}`,
                      () => {
                        const raw = (resumeDraft[job.id] ?? "").trim();
                        const budget = raw === "" ? undefined : Number(raw);
                        return resumeSeed(
                          job.id,
                          budget !== undefined && Number.isFinite(budget) && budget >= 0
                            ? budget
                            : undefined,
                        );
                      },
                      "Batch resumed",
                    )
                  }
                >
                  {busy === `resume:${job.id}` ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Play className="h-3.5 w-3.5" />
                  )}
                  <span className="ml-1">Resume</span>
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy !== null}
                  onClick={() => act(`cancel:${job.id}`, () => cancelSeed(job.id), "Batch cancelled")}
                >
                  {busy === `cancel:${job.id}` ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Square className="h-3.5 w-3.5" />
                  )}
                  <span className="ml-1">Cancel</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* Spend windows. */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Spend
        </h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {(["today", "week", "all"] as const).map((key) => (
            <SpendTile key={key} label={WINDOW_LABELS[key]} window={report?.spend?.[key]} />
          ))}
        </div>
        {report && report.metering_failures > 0 && (
          <p className="text-xs text-destructive">
            {report.metering_failures} usage row{report.metering_failures === 1 ? "" : "s"} could
            not be written, so the figures above are a floor
            {report.last_failure ? ` — ${report.last_failure}` : ""}.
          </p>
        )}
      </section>

      {/* The last batch: the Phase D number, with its denominator. */}
      {report?.last_job && (
        <section className="space-y-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Last batch
          </h3>
          <div className="rounded-lg bg-muted/40 p-2">
            <Row label="batch" value={<span className="font-mono">{report.last_job.job_id}</span>} />
            <Row
              label="attempts · rows"
              value={`${report.last_job.attempts} · ${report.last_job.rows_touched} rows`}
            />
            <Row
              label="retried"
              value={
                <span className={cn(report.last_job.retried_attempts > 0 && "text-amber-600 dark:text-amber-500")}>
                  {report.last_job.retried_attempts} of {report.last_job.attempts}
                </span>
              }
            />
            <Row label="tokens / row" value={num(report.last_job.tokens_per_row)} />
            <Row
              label="$ / row"
              value={money(report.last_job.cost_per_row)}
              tone={report.last_job.cost_complete ? undefined : "warn"}
            />
            {!report.last_job.cost_complete && (
              <p className="pt-0.5 text-[11px] text-amber-600 dark:text-amber-500">
                {report.last_job.unpriced_attempts} attempt
                {report.last_job.unpriced_attempts === 1 ? "" : "s"} had no price — $/row is a
                floor, not the bill
              </p>
            )}
          </div>
        </section>
      )}

      {/* Where the money went. */}
      {(report?.by_purpose.length ?? 0) > 0 && (
        <section className="space-y-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            By purpose · all time
          </h3>
          <div className="rounded-lg bg-muted/40 p-2">
            {report?.by_purpose.map((p) => (
              <Row
                key={p.purpose}
                label={p.purpose}
                value={`${p.attempts} calls · ${num(p.total_tokens)} tok · ${money(p.cost_usd)}${
                  p.unpriced_attempts > 0 ? ` (${p.unpriced_attempts} unpriced)` : ""
                }`}
              />
            ))}
          </div>
        </section>
      )}

      {(report?.by_model.length ?? 0) > 0 && (
        <section className="space-y-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            By model · all time
          </h3>
          <div className="rounded-lg bg-muted/40 p-2">
            {report?.by_model.map((m) => (
              <Row
                key={m.model}
                label={m.model}
                value={`${m.attempts} calls · ${num(m.total_tokens)} tok · ${money(m.cost_usd)}${
                  m.unpriced_attempts > 0 ? ` (${m.unpriced_attempts} unpriced)` : ""
                }`}
              />
            ))}
          </div>
        </section>
      )}

      {/* The brake. */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Budget per batch
        </h3>
        <p className="text-xs text-muted-foreground">
          One cap for each batch. When a batch reaches it, the batch <strong>parks</strong> — it
          keeps everything it wrote and waits for you here. Unset means unlimited, which is how
          this install behaves out of the box.
        </p>
        {budgetStatus && (
          <div className="rounded-lg bg-muted/40 p-2">
            <Row
              label="current cap"
              value={budgetStatus.budget_usd === null ? "unlimited (unset)" : money(budgetStatus.budget_usd)}
            />
            {budgetStatus.parse_error && (
              <Row label="ignored" value={budgetStatus.parse_error} tone="warn" />
            )}
            <Row label="rates used" value={`${budgetStatus.rates_origin} · ${budgetStatus.rate_version}`} />
          </div>
        )}
        <div className="flex flex-wrap items-end gap-2">
          <label className="space-y-0.5">
            <span className="block text-[11px] uppercase tracking-wider text-muted-foreground">
              new cap (USD)
            </span>
            <Input
              value={budgetDraft}
              onChange={(e) => setBudgetDraft(e.target.value)}
              inputMode="decimal"
              placeholder="unlimited"
              className="h-7 w-32 text-xs tabular-nums"
            />
          </label>
          <Button
            size="sm"
            disabled={busy !== null}
            onClick={() =>
              act(
                "budget",
                () => {
                  const raw = budgetDraft.trim();
                  const value = raw === "" ? null : Number(raw);
                  return setLlmBudget(value !== null && Number.isFinite(value) && value >= 0 ? value : null);
                },
                "Budget saved",
              )
            }
          >
            {busy === "budget" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            <span className="ml-1">Save cap</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={busy !== null}
            onClick={() => act("budget-clear", () => setLlmBudget(null), "Budget cleared (unlimited)")}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span className="ml-1">Unlimited</span>
          </Button>
        </div>
      </section>

      {/* The rate table. */}
      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Rate table · per 1M tokens, USD
          </h3>
          {report && (
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              {report.rates.origin === "builtin" ? (
                <>
                  <CircleCheck className="h-3 w-3 text-success" />
                  cited built-ins · {report.rates.as_of}
                </>
              ) : (
                <>
                  <Coins className="h-3 w-3 text-amber-600 dark:text-amber-500" />
                  your edits · v{report.rates.version}
                </>
              )}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Every priced row names the table version it used, so editing a price changes future
          rows only. A blank field means the price is unknown and calls are recorded unpriced —
          it never means free.
        </p>
        <div className="space-y-1.5">
          {Object.entries(report?.rates.models ?? {}).map(([model, row]) => (
            <RateEditorRow
              key={model}
              model={model}
              row={row}
              draft={ratesDraft[model] ?? { input: "", output: "", cached_input: "" }}
              onChange={(m, field, value) => {
                setRatesDirty(true);
                setRatesDraft((prev) => ({
                  ...prev,
                  [m]: { ...(prev[m] ?? { input: "", output: "", cached_input: "" }), [field]: value },
                }));
              }}
            />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={busy !== null || !ratesDirty} onClick={() => void saveRates()}>
            {busy === "rates" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            <span className="ml-1">Save rates</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={busy !== null}
            onClick={() =>
              act("rates-reset", async () => {
                setRatesDraft({});
                setRatesDirty(false);
                return clearLlmRates();
              }, "Back to the cited built-in rates")
            }
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span className="ml-1">Use built-ins</span>
          </Button>
          {ratesDirty && (
            <span className="text-[11px] text-amber-600 dark:text-amber-500">unsaved edits</span>
          )}
        </div>
      </section>
    </div>
  );
}
