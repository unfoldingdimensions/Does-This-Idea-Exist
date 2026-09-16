"use client";

import * as React from "react";
import {
  CircleAlert,
  CircleCheck,
  ExternalLink,
  Loader2,
  PlugZap,
  RefreshCw,
  RotateCcw,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AdminUnauthorized,
  fetchLlmGateways,
  resetActiveLlmGateway,
  setActiveLlmGateway,
  testLlmGateway,
  updateLlmGateway,
} from "@/lib/api";
import type {
  KeySource,
  LlmGateway,
  LlmGatewayPatch,
  LlmGatewayTestResult,
  LlmGatewaysView,
} from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The two facts an operator must be told before they press a switch, because
 * neither is obvious from the screen: seeds and teardown captures share one
 * client, and the gateway is resolved per call — so a switch lands mid-run.
 */
const DESCRIPTION =
  "Seeds and teardown captures share one LLM client, so switching the active gateway moves both. It resolves per call: the switch lands on the next LLM call, including one inside a run already in flight — a seed working through its candidates changes gateway partway through.";

// --- the switch guard, said in the words the API would use -------------------

/** `needs a key` / `needs a model` — the short reason, or null when switchable. */
export function gatewayBlockedShort(g: { has_key: boolean; model: string }): string | null {
  if (!g.has_key) return "needs a key";
  if (!g.model.trim()) return "needs a model";
  return null;
}

/**
 * The reason `POST .../active` would answer 400 with, spelled out far enough to
 * be actionable (the env var that would satisfy it, when there is one). The
 * panel disables the control on this text instead of offering an action the
 * server is guaranteed to refuse.
 */
export function gatewayBlockedReason(g: LlmGateway): string | null {
  const short = gatewayBlockedShort(g);
  if (!short) return null;
  if (short === "needs a key" && g.env_vars.length > 0) {
    return `needs a key — set ${g.env_vars.join(" or ")} in backend/.env, or paste one here`;
  }
  return short;
}

/** The badge the panel header shows: is the ACTIVE gateway switchable? */
export function gatewayBadge(view: LlmGatewaysView): string | undefined {
  const active = view.gateways.find((g) => g.id === view.active);
  if (active) return active.ready ? undefined : (gatewayBlockedShort(active) ?? "not ready");
  return view.effective.ready ? undefined : "not ready";
}

// --- the panel badge store ---------------------------------------------------

// The header badge has to be right BEFORE the section is ever opened, so it is
// fetched once per open; the section then keeps it honest by publishing every
// view it renders. No polling, no second source of truth: one module value.
let badgeValue: string | undefined;
const badgeListeners = new Set<() => void>();

function publishBadge(next: string | undefined): void {
  if (badgeValue === next) return;
  badgeValue = next;
  badgeListeners.forEach((l) => l());
}

function subscribeBadge(listener: () => void): () => void {
  badgeListeners.add(listener);
  return () => {
    badgeListeners.delete(listener);
  };
}

function readBadge(): string | undefined {
  return badgeValue;
}

/**
 * `needs a key` (etc.) while the active gateway cannot be switched to, else
 * undefined. `enabled` mirrors the panel being open with a token: the fetch is
 * pointless while locked, and a stale badge is worse than none.
 */
export function useLlmGatewayBadge(enabled: boolean): string | undefined {
  const value = React.useSyncExternalStore(subscribeBadge, readBadge, readBadge);
  React.useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    // Deferred: react-hooks v7 forbids synchronous setState in an effect body,
    // and the production path never resolves in this tick anyway.
    const t = window.setTimeout(() => {
      void fetchLlmGateways()
        .then((v) => {
          if (!cancelled) publishBadge(gatewayBadge(v));
        })
        // The badge is a hint; the section itself reports the real failure.
        .catch(() => {});
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [enabled]);
  return value;
}

// --- small pieces ------------------------------------------------------------

function failureText(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

function KeyStatePill({ source }: { source: KeySource }) {
  const pill: Record<KeySource, { text: string; className: string }> = {
    settings: { text: "Saved", className: "bg-success/15 text-success" },
    env: { text: "From .env", className: "bg-secondary text-secondary-foreground" },
    none: { text: "Not set", className: "bg-destructive/10 text-destructive" },
  };
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap",
        pill[source].className,
      )}
    >
      {pill[source].text}
    </span>
  );
}

function OverrideMark({ overridden }: { overridden: boolean }) {
  return overridden ? (
    <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-secondary-foreground">
      overridden
    </span>
  ) : (
    <span className="text-[10px] text-muted-foreground">default</span>
  );
}

/**
 * One card: the gateway's state, its three fields, and the two decisions
 * (test it / switch to it). All fields are free text because providers add
 * models faster than any list changes; `suggested_models` is only a datalist
 * convenience.
 */
function GatewayCard({
  g,
  onUpdated,
  onView,
  onLocked,
}: {
  g: LlmGateway;
  /** The PUT answered with the fresh row — render that, don't patch a guess. */
  onUpdated: (g: LlmGateway) => void;
  onView: (v: LlmGatewaysView) => void;
  onLocked: (msg?: string) => void;
}) {
  // The key field ALWAYS starts empty and is never populated from the API,
  // because no response ever carries the key (§2 of the contract).
  const [keyInput, setKeyInput] = React.useState("");
  const [modelInput, setModelInput] = React.useState(g.model);
  const [baseInput, setBaseInput] = React.useState(g.base_url);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [test, setTest] = React.useState<LlmGatewayTestResult | null>(null);

  const disabled = busy !== null;
  const blocked = gatewayBlockedReason(g);
  const modelDirty = modelInput.trim() !== "" && modelInput.trim() !== g.model;
  const baseDirty = baseInput.trim() !== "" && baseInput.trim() !== g.base_url;

  const patch = async (
    body: LlmGatewayPatch,
    kind: string,
    done: string,
    opts?: { clearKey?: boolean },
  ) => {
    setBusy(kind);
    try {
      const next = await updateLlmGateway(g.id, body);
      if (opts?.clearKey) setKeyInput("");
      onUpdated(next);
      toast.success(done);
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The gateway didn't take that change", {
          description: failureText(err, "Unknown error"),
        });
      }
    } finally {
      setBusy(null);
    }
  };

  const runTest = async () => {
    setBusy("test");
    try {
      // A result, not an exception: even `ok: false` (bad key, wrong model,
      // blocked target) is a 200 and gets rendered below.
      setTest(await testLlmGateway(g.id));
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The test couldn't run", {
          description: failureText(err, "Unknown error"),
        });
      }
    } finally {
      setBusy(null);
    }
  };

  const makeActive = async () => {
    setBusy("active");
    try {
      const view = await setActiveLlmGateway(g.id);
      onView(view);
      toast.success(`${g.label} is now the active gateway`);
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("The switch was refused", {
          description: failureText(err, "Unknown error"),
        });
      }
    } finally {
      setBusy(null);
    }
  };

  const keyPlaceholder = g.has_key
    ? `Saved ${g.key_hint} — paste a new key to replace`
    : "No key — paste one, or set it in backend/.env";

  const keyNote =
    g.key_source === "settings"
      ? "stored in settings.db — the .env fallback is ignored while this is set"
      : g.key_source === "env"
        ? `from ${g.env_vars.join(" / ")} — a pasted key overrides it`
        : g.env_vars.length > 0
          ? `no key yet — set ${g.env_vars.join(" / ")}, or paste one here`
          : "no key yet";

  return (
    <div className="space-y-2.5 rounded-lg bg-background/60 p-3">
      {/* Identity row: label, key state, active marker, docs */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-foreground">{g.label}</span>
        <KeyStatePill source={g.key_source} />
        {g.is_active && (
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary whitespace-nowrap">
            Active
          </span>
        )}
        <span className="font-mono text-[10px] text-muted-foreground">{g.id}</span>
        {g.docs_url && (
          <a
            href={g.docs_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 text-[10px] font-medium text-primary underline-offset-2 hover:underline"
          >
            docs
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        )}
      </div>

      {/* The effective pair, monospace and allowed to wrap — the fields below
          are the editable copy of the same two values. */}
      <p className="break-all font-mono text-[10px] text-muted-foreground">
        {g.base_url} · {g.model}
      </p>

      {g.notes && (
        <p className="text-[11px] leading-snug text-muted-foreground">{g.notes}</p>
      )}

      {/* API key — write-only, two explicit actions */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-2">
          <Label
            htmlFor={`llm-key-${g.id}`}
            className="text-[10px] font-medium tracking-wider text-muted-foreground uppercase"
          >
            API key
          </Label>
          <span className="text-[10px] text-muted-foreground">{keyNote}</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Input
            id={`llm-key-${g.id}`}
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={keyPlaceholder}
            disabled={disabled}
            className="h-8 min-w-0 flex-1 font-mono text-xs"
          />
          <Button
            size="sm"
            onClick={() => void patch({ api_key: keyInput.trim() }, "key", `${g.label}: key saved`, {
              clearKey: true,
            })}
            disabled={disabled || !keyInput.trim()}
          >
            {busy === "key" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save key
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              void patch({ api_key: "" }, "key-clear", `${g.label}: stored key cleared`)
            }
            disabled={disabled || !g.overrides.api_key}
            title={
              g.overrides.api_key
                ? "Clear the stored key — the .env fallback (if any) takes over again"
                : g.key_source === "env"
                  ? "No stored key to clear — the .env fallback is in use"
                  : "No stored key to clear"
            }
          >
            {busy === "key-clear" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Clear key
          </Button>
        </div>
      </div>

      {/* Model — free text, datalist for convenience, empty = default */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-2">
          <Label
            htmlFor={`llm-model-${g.id}`}
            className="text-[10px] font-medium tracking-wider text-muted-foreground uppercase"
          >
            Model
          </Label>
          <OverrideMark overridden={g.overrides.model} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Input
            id={`llm-model-${g.id}`}
            list={`llm-models-${g.id}`}
            value={modelInput}
            onChange={(e) => setModelInput(e.target.value)}
            placeholder={g.default_model}
            disabled={disabled}
            spellCheck={false}
            className="h-8 min-w-0 flex-1 font-mono text-xs"
          />
          <datalist id={`llm-models-${g.id}`}>
            {g.suggested_models.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
          <Button
            size="sm"
            onClick={() => void patch({ model: modelInput.trim() }, "model", `${g.label}: model saved`)}
            disabled={disabled || !modelDirty}
          >
            {busy === "model" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void patch({ model: "" }, "model-reset", `${g.label}: model back to default`)}
            disabled={disabled || !g.overrides.model}
            title={
              g.overrides.model
                ? `Reset to the default model (${g.default_model})`
                : `Already on the default model (${g.default_model})`
            }
          >
            {busy === "model-reset" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            Reset
          </Button>
        </div>
      </div>

      {/* Base URL — free text, the field that makes a moved endpoint a settings edit */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-2">
          <Label
            htmlFor={`llm-base-${g.id}`}
            className="text-[10px] font-medium tracking-wider text-muted-foreground uppercase"
          >
            Base URL
          </Label>
          <OverrideMark overridden={g.overrides.base_url} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Input
            id={`llm-base-${g.id}`}
            value={baseInput}
            onChange={(e) => setBaseInput(e.target.value)}
            placeholder={g.default_base_url}
            disabled={disabled}
            spellCheck={false}
            className="h-8 min-w-0 flex-1 font-mono text-xs"
          />
          <Button
            size="sm"
            onClick={() =>
              void patch({ base_url: baseInput.trim() }, "base", `${g.label}: base URL saved`)
            }
            disabled={disabled || !baseDirty}
          >
            {busy === "base" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              void patch({ base_url: "" }, "base-reset", `${g.label}: base URL back to default`)
            }
            disabled={disabled || !g.overrides.base_url}
            title={
              g.overrides.base_url
                ? `Reset to the default base URL (${g.default_base_url})`
                : `Already on the default base URL (${g.default_base_url})`
            }
          >
            {busy === "base-reset" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            Reset
          </Button>
        </div>
      </div>

      {/* Test before you switch — this is the button that diagnoses a bad key */}
      <div className="flex flex-wrap items-center gap-1.5">
        <Button variant="outline" size="sm" onClick={() => void runTest()} disabled={disabled}>
          {busy === "test" ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <PlugZap className="h-3.5 w-3.5" />
          )}
          Test
        </Button>

        {!g.is_active &&
          (blocked ? (
            // The switch guard refuses this with a 400, so the control is
            // disabled and says why — the UI never offers a call that fails.
            <span className="inline-flex flex-wrap items-center gap-1.5" title={blocked}>
              <Button size="sm" disabled aria-disabled="true">
                <Zap className="h-3.5 w-3.5" aria-hidden="true" />
                Make active
              </Button>
              <span className="text-[10px] text-muted-foreground">{blocked}</span>
            </span>
          ) : (
            <Button size="sm" onClick={() => void makeActive()} disabled={disabled}>
              {busy === "active" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Zap className="h-3.5 w-3.5" />
              )}
              Make active
            </Button>
          ))}
      </div>

      {test && (
        <div
          role="status"
          className={cn(
            "space-y-0.5 rounded-md px-2 py-1.5 text-[10px]",
            test.ok ? "bg-success/10" : "bg-destructive/10",
          )}
        >
          <p
            className={cn(
              "flex items-center gap-1 font-semibold",
              test.ok ? "text-success" : "text-destructive",
            )}
          >
            {test.ok ? (
              <CircleCheck className="h-3 w-3" aria-hidden="true" />
            ) : (
              <CircleAlert className="h-3 w-3" aria-hidden="true" />
            )}
            {test.ok ? "ok" : "failed"} · <span className="tabular-nums">{test.latency_ms} ms</span>
            {typeof test.http_status === "number" && (
              <span className="font-normal"> · HTTP {test.http_status}</span>
            )}
          </p>
          {test.ok ? (
            <p className="text-muted-foreground">
              reply <span className="font-mono text-foreground">{test.reply ?? "—"}</span>
              {test.model_echoed && (
                <>
                  {" "}
                  · model echoed{" "}
                  <span className="font-mono text-foreground">{test.model_echoed}</span>
                </>
              )}
            </p>
          ) : (
            // The provider's own text, verbatim — a wrong model and a bad key
            // (and a blocked target) are told apart by it, and a generic line
            // would throw that away.
            <p className="max-h-32 overflow-y-auto break-words font-mono text-destructive">
              {test.error ?? "the provider returned no error text"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * LLM gateways — which OpenAI-compatible surface every seed and capture talks
 * to, the key each one has (never its value), and the switch itself
 * (`docs/llm-gateways.md` §4).
 */
export function LlmGatewaysSection({ onLocked }: { onLocked: (msg?: string) => void }) {
  const [view, setView] = React.useState<LlmGatewaysView | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [resetting, setResetting] = React.useState(false);
  const aliveRef = React.useRef(true);

  React.useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const next = await fetchLlmGateways();
      if (!aliveRef.current) return;
      setView(next);
    } catch (err) {
      if (!aliveRef.current) return;
      if (err instanceof AdminUnauthorized) {
        const locked = "Admin session expired — re-enter your token";
        setLoadError(locked);
        onLocked(locked);
        return;
      }
      const msg = failureText(err, "Couldn't read the gateway settings");
      setLoadError(msg);
      toast.error("Couldn't read the gateway settings", { description: msg });
    } finally {
      if (aliveRef.current) setLoading(false);
    }
  }, [onLocked]);

  React.useEffect(() => {
    // Deferred via timer: react-hooks v7 forbids synchronous setState in an
    // effect body (same pattern as the verification section's initial load).
    const t = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(t);
  }, [load]);

  // Keep the panel header badge honest without a second request.
  React.useEffect(() => {
    if (view) publishBadge(gatewayBadge(view));
  }, [view]);

  /** The PUT answered with one fresh row — splice that in, and refresh the
   * effective line too when the row that changed is the active one. */
  const applyGateway = React.useCallback((next: LlmGateway) => {
    setView((v) => {
      if (!v) return v;
      const gateways = v.gateways.map((x) => (x.id === next.id ? next : x));
      if (!next.is_active) return { ...v, gateways };
      return {
        ...v,
        gateways,
        effective: {
          gateway_id: next.id,
          label: next.label,
          base_url: next.base_url,
          model: next.model,
          has_key: next.has_key,
          key_source: next.key_source,
          ready: next.ready,
        },
      };
    });
  }, []);

  const resetActive = async () => {
    setResetting(true);
    try {
      const next = await resetActiveLlmGateway();
      setView(next);
      toast.success("Back to the gateway backend/.env describes");
    } catch (err) {
      if (err instanceof AdminUnauthorized) {
        onLocked("Admin session expired — re-enter your token");
      } else {
        toast.error("Couldn't reset the active gateway", {
          description: failureText(err, "Unknown error"),
        });
      }
    } finally {
      setResetting(false);
    }
  };

  const effective = view?.effective;
  const effectiveShort = effective ? gatewayBlockedShort(effective) : null;

  return (
    <div className="space-y-3 pt-2">
      <p className="text-xs text-muted-foreground">{DESCRIPTION}</p>

      {!view ? (
        loading ? (
          <p className="flex items-center gap-2 rounded-lg bg-background/60 p-3 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Reading the gateway settings…
          </p>
        ) : (
          <div className="space-y-2 rounded-lg bg-background/60 p-3">
            <p className="text-xs text-destructive">
              {loadError ?? "Couldn't read the gateway settings"}
            </p>
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Retry
            </Button>
          </div>
        )
      ) : (
        <>
          {/* What an LLM call would use right now */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
            <div className="min-w-0 space-y-0.5">
              <p className="flex flex-wrap items-center gap-1.5">
                <span className="text-muted-foreground">In use right now</span>
                <span className="font-medium text-foreground">{effective?.label}</span>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap",
                    effective?.ready
                      ? "bg-success/15 text-success"
                      : "bg-destructive/10 text-destructive",
                  )}
                >
                  {effective?.ready ? "ready" : (effectiveShort ?? "not ready")}
                </span>
              </p>
              <p className="break-all font-mono text-[10px] text-muted-foreground">
                {effective?.base_url} · {effective?.model}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void resetActive()}
              disabled={resetting}
              title="Back to the gateway backend/.env describes (POST /active/reset)"
            >
              {resetting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5" />
              )}
              Reset to default gateway
            </Button>
          </div>

          {view.gateways.map((g) => (
            <GatewayCard
              // Keyed on the server's answer: a successful write remounts the
              // card so its fields show the values the API just returned, and
              // a stale test result is dropped with it.
              key={cardKey(g)}
              g={g}
              onUpdated={applyGateway}
              onView={setView}
              onLocked={onLocked}
            />
          ))}

          <p className="text-[10px] text-muted-foreground">
            A stored key is write-only: no response ever contains it, so the field starts
            empty every time and shows only the last four characters.
          </p>
        </>
      )}
    </div>
  );
}

/** Anything a write can change, so the card remounts exactly when it must. */
function cardKey(g: LlmGateway): string {
  return [
    g.id,
    g.model,
    g.base_url,
    g.key_source,
    g.key_hint,
    g.overrides.api_key ? "k" : "",
    g.overrides.model ? "m" : "",
    g.overrides.base_url ? "b" : "",
    g.is_active ? "a" : "",
    g.ready ? "r" : "",
  ].join("|");
}
