"use client";

import * as React from "react";
import {
  Check,
  CheckCircle2,
  ClipboardCopy,
  Info,
  Loader2,
  Plus,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  confirmFounderApp,
  createFounderApp,
  getFounderApp,
  publishFounderApp,
} from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import type {
  ArchiveStatus,
  FounderAppDraft,
  FounderProfile,
  FounderSubmission,
  PricingPlan,
} from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Your own app — the "you" side of every comparison.
 *
 * Three ingest paths, one record, and a hard flow of **ingest → confirm → diff**
 * (docs/teardown-spec.md §3): a URL, the short form, or a structured JSON blob
 * pasted from the founder's own agent. Nothing is auto-confirmed and nothing
 * auto-diffs — the review step is mandatory, and `onCommitted` only fires once
 * the confirm gate is passed, so the parent can never open the gap table against
 * a machine draft.
 *
 * `archive_status` is shown at all times once a draft exists: with no accounts,
 * the submission row is the entire feedback loop, so a rejected request has to be
 * visible here rather than vanishing. Two gates, deliberately not merged (§3.1):
 * eligibility (a real link) decides whether the consent question is even asked,
 * and consent (the opt-in) is what queues the app behind the same admin gate as
 * any competitor.
 *
 * No `publish` field is ever sent on create — that is a 422 on purpose. The
 * lifecycle is exactly three calls: create → confirm → publish.
 */

const CATEGORIES = [
  "productivity",
  "ai",
  "devtools",
  "desktop",
  "freelance",
  "finance",
  "health",
  "education",
  "ecommerce",
  "social",
  "media",
  "other",
] as const;

const FEATURE_MIN = 5;
const FEATURE_MAX = 10;

/**
 * The copy-paste prompt from docs/teardown-spec.md §3, reproduced verbatim so the
 * founder can hand their own agent the exact shape this endpoint accepts.
 */
const AGENT_PROMPT = `Describe my app in a strict JSON object with exactly these keys, no extra prose:

{
  "name": "string — display name",
  "description": "string — 2-3 sentences: what it is, who it's for, what problem it solves",
  "target_user": "string — one sentence naming the primary user",
  "category": "one of: productivity, ai, devtools, desktop, freelance, finance, health, education, ecommerce, social, media, other",
  "features": ["5 to 10 short capability strings, one per item, e.g. 'local files', 'real-time collaboration', 'public API'"],
  "positioning": "string — one line: how you describe yourselves and who it's for",
  "pricing": {
    "free_tier": "string — e.g. 'Free up to 3 docs', or 'No free tier'",
    "plans": [{"name": "string", "price": "string — e.g. '$8/mo' or 'custom'", "period": "monthly|annual|one-time"}]
  },
  "links": {
    "website": "string — or \\"\\" if none",
    "app_store": "string — or \\"\\" if none",
    "play_store": "string — or \\"\\" if none",
    "github": "string — or \\"\\" if none"
  }
}

Rules: use only facts about my app. Keep features to 5-10 items. Do not invent a feature
or a price I did not state. If a field is unknown, use "" or []. Output JSON only.
Links are optional — but note that an app with no link can be compared and will never
be added to the archive.`;

type TabKey = "url" | "form" | "agent";

interface FormState {
  name: string;
  description: string;
  targetUser: string;
  category: string;
  features: string;
  positioning: string;
  freeTier: string;
  plans: PricingPlan[];
  websiteUrl: string;
  githubUrl: string;
  appStoreUrl: string;
  playStoreUrl: string;
}

function makeEmptyForm(): FormState {
  return {
    name: "",
    description: "",
    targetUser: "",
    category: "",
    features: "",
    positioning: "",
    freeTier: "",
    plans: [{ name: "", price: "", period: "" }],
    websiteUrl: "",
    githubUrl: "",
    appStoreUrl: "",
    playStoreUrl: "",
  };
}

const STATUS_META: Record<
  ArchiveStatus,
  { label: string; hint: string; className: string }
> = {
  local_only: {
    label: "Local only",
    hint: "In your founder store only. Nothing has been submitted to the archive.",
    className: "border-border bg-muted text-muted-foreground",
  },
  pending: {
    label: "Pending review",
    hint: "Submitted — waiting on the same admin gate as every competitor.",
    className: "border-primary/25 bg-primary/10 text-primary",
  },
  approved: {
    label: "In the archive",
    hint: "Approved — your app now sits in the archive alongside its competitors.",
    className: "border-success/25 bg-success/12 text-success",
  },
  rejected: {
    label: "Not accepted",
    hint: "The request was reviewed and turned down. The note below says why.",
    className: "border-destructive/25 bg-destructive/10 text-destructive",
  },
  withdrawn: {
    label: "Withdrawn",
    hint: "Pulled from the queue. You can resubmit at any time.",
    className: "border-border bg-muted text-muted-foreground",
  },
};

const SOURCE_LABEL: Record<NonNullable<FounderAppDraft["source_kind"]>, string> = {
  url: "Drafted from your website URL",
  form: "Entered in the form",
  agent_json: "Pasted from your agent",
};

const SUBMISSION_LABEL: Record<FounderSubmission["status"], string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

/** http(s) only — anything else would fail the backend fetch anyway. */
function isHttpUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/** Features arrive one per line or comma-separated — split, trim, drop blanks. */
function parseFeatures(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * The local 5-10 rule, worded loudly on purpose: the gap table compares feature
 * by feature, so a short list is not a small oversight — it makes the whole
 * comparison hollow (docs/teardown-spec.md §3).
 */
function featureCountMessage(count: number): string | null {
  if (count === 0) {
    return `A feature list is required — add ${FEATURE_MIN}–${FEATURE_MAX} short capabilities, one per line.`;
  }
  if (count < FEATURE_MIN) {
    return `Only ${count} feature${
      count === 1 ? "" : "s"
    } — fewer than ${FEATURE_MIN} makes the comparison hollow. Add ${
      FEATURE_MIN - count
    } more (${FEATURE_MIN}–${FEATURE_MAX} total).`;
  }
  if (count > FEATURE_MAX) {
    return `That's ${count} features — keep it to ${FEATURE_MAX} at most.`;
  }
  return null;
}

/** The newest submission row, by id (the same ordering the backend derives from). */
function newestSubmission(
  submissions: FounderSubmission[],
  fallback: FounderSubmission | null,
): FounderSubmission | null {
  let best = fallback;
  for (const s of submissions) {
    if (!best || s.id > best.id) best = s;
  }
  return best;
}

function ReviewField({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 text-[13px] leading-relaxed">{children}</dd>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </h4>
  );
}

/** The drafted profile, every field shown — the thing the founder confirms. */
function ProfileReview({
  profile,
  sourceKind,
}: {
  profile: FounderProfile;
  sourceKind: FounderAppDraft["source_kind"];
}) {
  const features = profile.features ?? [];
  const plans = profile.pricing?.plans ?? [];
  const links: { label: string; url: string | null }[] = [
    { label: "Website", url: profile.website_url },
    { label: "GitHub", url: profile.github_url },
    { label: "App Store", url: profile.app_store_url },
    { label: "Play Store", url: profile.play_store_url },
  ];

  return (
    <div className="space-y-4 rounded-3xl border border-border/60 bg-background/40 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="text-[11px]">
          {sourceKind ? SOURCE_LABEL[sourceKind] : "Unknown source"}
        </Badge>
        {profile.category ? (
          <Badge variant="outline" className="text-[11px]">
            {titleCase(profile.category)}
          </Badge>
        ) : null}
      </div>

      <div>
        <h3 className="font-display text-lg font-semibold leading-tight">
          {profile.name || "—"}
        </h3>
        {profile.tagline ? (
          <p className="mt-0.5 text-[13px] font-medium text-muted-foreground">
            {profile.tagline}
          </p>
        ) : null}
      </div>

      <dl className="grid gap-3 sm:grid-cols-2">
        <ReviewField label="Description" className="sm:col-span-2">
          {profile.description ? (
            <span className="whitespace-pre-wrap">{profile.description}</span>
          ) : (
            "—"
          )}
        </ReviewField>
        <ReviewField label="Target user" className="sm:col-span-2">
          {profile.target_users || "—"}
        </ReviewField>
        <ReviewField label="Positioning" className="sm:col-span-2">
          {profile.positioning || "—"}
        </ReviewField>
      </dl>

      <div>
        <SectionLabel>Features ({features.length})</SectionLabel>
        {features.length ? (
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {features.map((feature, i) => (
              <li
                key={`${feature}-${i}`}
                className="rounded-full border border-border/60 bg-muted/50 px-2.5 py-0.5 text-[12px]"
              >
                {feature}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            None yet — the URL path deliberately leaves features empty.
          </p>
        )}
      </div>

      <div>
        <SectionLabel>Pricing</SectionLabel>
        <div className="mt-1.5 space-y-1 text-[13px]">
          <p>
            <span className="text-muted-foreground">Free tier: </span>
            {profile.pricing?.free_tier || "—"}
          </p>
          {plans.length ? (
            <ul className="space-y-0.5">
              {plans.map((plan, i) => (
                <li key={`${plan.name}-${i}`} className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{plan.name || "Untitled plan"}</span>
                  <span className="text-muted-foreground">
                    {plan.price}
                    {plan.period ? ` · ${plan.period}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">No plans listed.</p>
          )}
        </div>
      </div>

      <div>
        <SectionLabel>Links</SectionLabel>
        <ul className="mt-1.5 grid gap-1 text-[13px] sm:grid-cols-2">
          {links.map((link) => (
            <li key={link.label} className="flex min-w-0 items-baseline gap-1.5">
              <span className="shrink-0 text-muted-foreground">{link.label}:</span>
              {link.url ? (
                <a
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-primary underline-offset-2 hover:underline"
                >
                  {link.url}
                </a>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/**
 * The status + eligibility + consent surface. Shown the moment a draft exists
 * (the founder's only feedback loop) and re-rendered from every write response,
 * so what is on screen is the real current state.
 */
function StatusPanel({
  draft,
  submissions,
  consent,
  onConsentChange,
  canPublish,
  busy,
  onPublish,
}: {
  draft: FounderAppDraft;
  submissions: FounderSubmission[];
  consent: boolean;
  onConsentChange: (v: boolean) => void;
  canPublish: boolean;
  busy: boolean;
  onPublish: () => void;
}) {
  const status = draft.archive_status;
  const meta = STATUS_META[status];
  const newest = newestSubmission(submissions, draft.submission);
  const showRejection = status === "rejected" && newest?.status === "rejected";

  return (
    <section
      aria-labelledby="founder-status-heading"
      className="space-y-3 rounded-3xl border border-border/60 bg-background/40 p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="founder-status-heading" className="text-sm font-semibold">
          Archive status
        </h3>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
            meta.className,
          )}
        >
          <span aria-hidden className="size-1.5 rounded-full bg-current" />
          {meta.label}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{meta.hint}</p>

      {showRejection && newest ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-destructive">
            Why it was turned down
          </p>
          <p className="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-destructive">
            {newest.note?.trim() || "No note was recorded."}
          </p>
          <p className="mt-1.5 text-[11px] leading-relaxed text-destructive/80">
            Decided {formatDate(newest.decided_at ?? newest.submitted_at)}. A resubmission is
            a new row — the history below stays auditable.
          </p>
        </div>
      ) : null}

      {!draft.publish_offered ? (
        <div className="rounded-2xl border border-border/60 bg-muted/40 p-3">
          <p className="text-[13px] leading-relaxed">
            <span className="font-medium">No link — comparison only.</span> Your app has no
            website, GitHub, App Store, or Play Store link, so it will never be added to the
            archive: no link → no archive entry. Add any one of{" "}
            <span className="font-medium">
              website URL · GitHub · App Store URL · Play Store URL
            </span>{" "}
            to make it eligible.
          </p>
        </div>
      ) : !draft.confirmed ? (
        <div className="rounded-2xl border border-border/60 bg-muted/40 p-3 text-[13px] leading-relaxed text-muted-foreground">
          This app has a link, so it is eligible for the archive. Confirm your draft first —
          consent is not approval, and publication is only offered once you have confirmed.
        </div>
      ) : canPublish ? (
        <div className="space-y-2 rounded-2xl border border-border/60 p-3">
          <label className="flex items-start gap-2.5 text-[13px] leading-relaxed">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => onConsentChange(e.target.checked)}
              disabled={busy}
              className="mt-0.5 size-4 shrink-0 accent-[var(--primary)]"
            />
            <span>
              Add <span className="font-medium">{draft.profile.name || "my app"}</span> to the
              archive. It joins the same admin approval queue as every competitor, and I
              understand it can be turned down with a note.
            </span>
          </label>
          <div className="flex justify-end">
            <Button type="button" size="sm" onClick={onPublish} disabled={busy || !consent}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
              Submit for publication
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-border/60 bg-muted/40 p-3 text-[13px] leading-relaxed text-muted-foreground">
          {status === "pending"
            ? "A publish request is already pending review — its outcome will appear here."
            : status === "approved"
              ? "This app is already in the archive; no further request is needed."
              : "Publication is not available for this draft right now."}
        </div>
      )}

      {submissions.length > 0 ? (
        <div>
          <SectionLabel>Submission history</SectionLabel>
          <ul className="mt-1.5 space-y-1">
            {submissions.map((submission) => (
              <li
                key={submission.id}
                className="flex flex-wrap items-baseline gap-x-2 text-[12px]"
              >
                <span className="font-medium">{SUBMISSION_LABEL[submission.status]}</span>
                <span className="text-muted-foreground">
                  {formatDate(submission.decided_at ?? submission.submitted_at)}
                </span>
                {submission.note ? (
                  <span className="text-muted-foreground">— {submission.note}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

/**
 * The wizard body. Kept separate from the Dialog shell so Radix unmounts it (and
 * discards every field) when the dialog closes — a reopened modal starts from a
 * clean draft instead of showing the previous founder's profile.
 */
function FounderAppWizard({
  onCommitted,
}: {
  onCommitted?: (draft: FounderAppDraft) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [draft, setDraft] = React.useState<FounderAppDraft | null>(null);
  const [submissions, setSubmissions] = React.useState<FounderSubmission[]>([]);
  const [tab, setTab] = React.useState<TabKey>("url");

  // URL path
  const [url, setUrl] = React.useState("");
  const [nameHint, setNameHint] = React.useState("");

  // Form path
  const [form, setForm] = React.useState<FormState>(makeEmptyForm);

  // Agent path
  const [agentJson, setAgentJson] = React.useState("");

  // Consent gate
  const [consent, setConsent] = React.useState(false);

  const resetAll = () => {
    setBusy(false);
    setError(null);
    setDraft(null);
    setSubmissions([]);
    setTab("url");
    setUrl("");
    setNameHint("");
    setForm(makeEmptyForm());
    setAgentJson("");
    setConsent(false);
  };

  /** Pull the authoritative draft + full decision history. Best-effort: a
   * failed read leaves the write response on screen rather than blanking it. */
  const loadDetail = async (id: number) => {
    try {
      const detail = await getFounderApp(id);
      setDraft(detail);
      setSubmissions(detail.submissions);
    } catch {
      /* keep whatever the write response gave us */
    }
  };

  const runCreate = async (body: Record<string, unknown>, label: string) => {
    setBusy(true);
    setError(null);
    try {
      const created = await createFounderApp(body);
      setDraft(created);
      setSubmissions(created.submission ? [created.submission] : []);
      setConsent(false);
      toast.success(`${label} created`, {
        description: "Review it, then confirm — nothing runs until you do.",
      });
      void loadDetail(created.founder_app_id);
    } catch (err) {
      // The server's own text, verbatim — a malformed JSON body, an unknown key
      // in the agent payload, or a feature list under five are each their own
      // message, and swallowing them into "something went wrong" would hide the
      // one thing the founder needs to fix.
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const submitUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const value = url.trim();
    if (!value) {
      setError("Enter your app's URL first.");
      return;
    }
    if (!isHttpUrl(value)) {
      setError("That doesn't look like a valid URL — include https://");
      return;
    }
    const hint = nameHint.trim();
    void runCreate(
      hint ? { url: value, name_hint: hint } : { url: value },
      "Draft from URL",
    );
  };

  const submitForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const name = form.name.trim();
    if (!name) {
      setError("A name is required.");
      return;
    }
    const features = parseFeatures(form.features);
    const featureError = featureCountMessage(features.length);
    if (featureError) {
      setError(featureError);
      return;
    }

    const body: Record<string, unknown> = { name, features };
    if (form.description.trim()) body.description = form.description.trim();
    if (form.targetUser.trim()) body.target_user = form.targetUser.trim();
    if (form.category) body.category = form.category;
    if (form.positioning.trim()) body.positioning = form.positioning.trim();

    const plans = form.plans
      .map((p) => ({
        name: p.name.trim(),
        price: p.price.trim(),
        period: p.period.trim(),
      }))
      .filter((p) => p.name || p.price || p.period);
    const pricing: { free_tier?: string; plans?: PricingPlan[] } = {};
    if (form.freeTier.trim()) pricing.free_tier = form.freeTier.trim();
    if (plans.length) pricing.plans = plans;
    if (pricing.free_tier || pricing.plans) body.pricing = pricing;

    if (form.websiteUrl.trim()) body.website_url = form.websiteUrl.trim();
    if (form.githubUrl.trim()) body.github_url = form.githubUrl.trim();
    if (form.appStoreUrl.trim()) body.app_store_url = form.appStoreUrl.trim();
    if (form.playStoreUrl.trim()) body.play_store_url = form.playStoreUrl.trim();

    // No `publish` key, ever: it is a 422 on purpose.
    void runCreate(body, "Form draft");
  };

  const submitAgent = (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const text = agentJson.trim();
    if (!text) {
      setError("Paste your agent's JSON first.");
      return;
    }
    void runCreate({ agent_json: text }, "Agent draft");
  };

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(AGENT_PROMPT);
      toast.success("Prompt copied", {
        description: "Paste it into your agent, then bring the JSON back here.",
      });
    } catch {
      toast.error("Couldn't copy the prompt", {
        description: "Clipboard access was blocked — select the text and copy it by hand.",
      });
    }
  };

  const runConfirm = async () => {
    if (!draft || busy) return;
    setBusy(true);
    setError(null);
    try {
      const confirmed = await confirmFounderApp(draft.founder_app_id);
      setDraft(confirmed);
      toast.success("Draft confirmed", {
        description: "This is your record now — the gap table can run against it.",
      });
      // The gap table only ever becomes reachable past this gate.
      onCommitted?.(confirmed);
      void loadDetail(confirmed.founder_app_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't confirm the draft.");
    } finally {
      setBusy(false);
    }
  };

  const runPublish = async () => {
    if (!draft || busy || !consent) return;
    const id = draft.founder_app_id;
    setBusy(true);
    setError(null);
    try {
      const res = await publishFounderApp(id);
      // Re-render from the response, then re-fetch for the full history.
      setDraft((prev) => (prev ? { ...prev, archive_status: res.archive_status } : prev));
      setConsent(false);
      toast.success("Submitted to the archive", {
        description: "It now waits on the same admin gate as any competitor.",
      });
      void loadDetail(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't submit for publication.");
    } finally {
      setBusy(false);
    }
  };

  const featureCount = draft ? (draft.profile.features ?? []).length : 0;
  const canPublish =
    !!draft &&
    draft.publish_offered &&
    draft.confirmed &&
    (draft.archive_status === "local_only" ||
      draft.archive_status === "rejected" ||
      draft.archive_status === "withdrawn");

  const updatePlan = (index: number, key: keyof PricingPlan, value: string) => {
    setForm((f) => ({
      ...f,
      plans: f.plans.map((p, i) => (i === index ? { ...p, [key]: value } : p)),
    }));
  };
  const addPlan = () =>
    setForm((f) => ({ ...f, plans: [...f.plans, { name: "", price: "", period: "" }] }));
  const removePlan = (index: number) =>
    setForm((f) => ({ ...f, plans: f.plans.filter((_, i) => i !== index) }));

  return (
    <>
      <DialogHeader>
        <DialogTitle>Your app</DialogTitle>
        <DialogDescription>
          Draft it, review it, confirm it. This profile is the “you” side of every
          comparison — the gap table never runs against an unconfirmed draft.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4">
        {error ? (
          <p
            role="alert"
            className="rounded-2xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-[13px] leading-relaxed text-destructive"
          >
            {error}
          </p>
        ) : null}

        {draft ? (
          <div className="space-y-4">
            {draft.confirmed ? (
              <div className="flex items-start gap-2.5 rounded-2xl border border-success/30 bg-success/10 p-3">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
                <p className="text-[13px] leading-relaxed">
                  <span className="font-medium">Confirmed.</span> This is your record now —
                  the gap table can run against it.
                </p>
              </div>
            ) : (
              <div className="flex items-start gap-2.5 rounded-2xl border border-border bg-muted/50 p-3">
                <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <p className="text-[13px] leading-relaxed">
                  <span className="font-medium">Machine draft — not confirmed.</span> Review
                  every field below. The gap table will not run until you confirm, so nothing
                  is ever compared against a guess.
                </p>
              </div>
            )}

            <ProfileReview profile={draft.profile} sourceKind={draft.source_kind} />

            {featureCount < FEATURE_MIN ? (
              <p
                role="status"
                className="rounded-2xl border border-destructive/30 bg-destructive/10 p-3 text-[13px] leading-relaxed text-destructive"
              >
                {featureCount === 0
                  ? "This draft has no features. Fewer than 5 makes the comparison hollow — add them from the Form or agent path, then draft again."
                  : `Only ${featureCount} feature${
                      featureCount === 1 ? "" : "s"
                    } — fewer than ${FEATURE_MIN} makes the comparison hollow.`}
              </p>
            ) : null}

            {!draft.confirmed ? (
              <div className="flex justify-end">
                <Button type="button" onClick={runConfirm} disabled={busy}>
                  {busy ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Check className="size-4" />
                  )}
                  Confirm this draft
                </Button>
              </div>
            ) : null}

            <StatusPanel
              draft={draft}
              submissions={submissions}
              consent={consent}
              onConsentChange={setConsent}
              canPublish={canPublish}
              busy={busy}
              onPublish={runPublish}
            />

            <div className="flex items-center justify-between gap-2 pt-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetAll}
                disabled={busy}
              >
                Start over
              </Button>
              <DialogClose asChild>
                <Button type="button" variant="outline" size="sm">
                  Close
                </Button>
              </DialogClose>
            </div>
          </div>
        ) : (
          <Tabs
            value={tab}
            onValueChange={(v) => {
              setError(null);
              setTab(v as TabKey);
            }}
          >
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="url">URL</TabsTrigger>
              <TabsTrigger value="form">Form</TabsTrigger>
              <TabsTrigger value="agent">Paste agent JSON</TabsTrigger>
            </TabsList>

            <TabsContent value="url">
              <form onSubmit={submitUrl} className="space-y-3 pt-3">
                <div className="space-y-1.5">
                  <Label htmlFor="fa-url">Your app&apos;s URL</Label>
                  <Input
                    id="fa-url"
                    placeholder="https://yourapp.com"
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      setError(null);
                    }}
                    disabled={busy}
                    autoFocus
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="fa-name-hint">Name hint (optional)</Label>
                  <Input
                    id="fa-name-hint"
                    placeholder="App name — auto-detected if empty"
                    value={nameHint}
                    onChange={(e) => setNameHint(e.target.value)}
                    disabled={busy}
                  />
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Drafts{" "}
                  <span className="font-medium text-foreground">
                    name, tagline, category, description and founded
                  </span>{" "}
                  from the page — the same primitive that drafts a competitor. Features are
                  deliberately left empty: the URL path must not invent your feature list.
                  You&apos;ll fill them in from the Form or agent path.
                </p>
                <div className="flex justify-end pt-1">
                  <Button type="submit" disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Draft from URL
                  </Button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="form">
              <form onSubmit={submitForm} className="space-y-3 pt-3">
                <div className="space-y-1.5">
                  <Label htmlFor="fa-name">Name *</Label>
                  <Input
                    id="fa-name"
                    placeholder="Your app's name"
                    value={form.name}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, name: e.target.value }));
                      setError(null);
                    }}
                    disabled={busy}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-description">One-line description</Label>
                  <Textarea
                    id="fa-description"
                    rows={2}
                    placeholder="What it is, in a sentence or two"
                    value={form.description}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, description: e.target.value }))
                    }
                    disabled={busy}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-target">Target user</Label>
                  <Input
                    id="fa-target"
                    placeholder="Who it's for"
                    value={form.targetUser}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, targetUser: e.target.value }))
                    }
                    disabled={busy}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-category">Category</Label>
                  <Select
                    value={form.category}
                    onValueChange={(v) => setForm((f) => ({ ...f, category: v }))}
                  >
                    <SelectTrigger id="fa-category" className="w-full">
                      <SelectValue placeholder="Choose a category" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {titleCase(c)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-features">Features * (5–10, one per line)</Label>
                  <Textarea
                    id="fa-features"
                    rows={6}
                    placeholder={"real-time collaboration\npublic API\nlocal files"}
                    value={form.features}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, features: e.target.value }));
                      setError(null);
                    }}
                    disabled={busy}
                    aria-describedby="fa-features-help"
                  />
                  <p
                    id="fa-features-help"
                    className={cn(
                      "text-xs",
                      featureCountMessage(parseFeatures(form.features).length)
                        ? "text-destructive"
                        : "text-muted-foreground",
                    )}
                  >
                    {parseFeatures(form.features).length} so far — needs 5–10; the gap table
                    compares feature by feature.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-positioning">Positioning (one line)</Label>
                  <Input
                    id="fa-positioning"
                    placeholder="How you describe yourselves and who it's for"
                    value={form.positioning}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, positioning: e.target.value }))
                    }
                    disabled={busy}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="fa-free-tier">Pricing — free tier</Label>
                  <Input
                    id="fa-free-tier"
                    placeholder="e.g. Free up to 3 docs — or 'No free tier'"
                    value={form.freeTier}
                    onChange={(e) => setForm((f) => ({ ...f, freeTier: e.target.value }))}
                    disabled={busy}
                  />
                  <div className="space-y-2 pt-1">
                    {form.plans.map((plan, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <Input
                          aria-label={`Plan ${i + 1} name`}
                          placeholder="Name"
                          value={plan.name}
                          onChange={(e) => updatePlan(i, "name", e.target.value)}
                          disabled={busy}
                          className="flex-1"
                        />
                        <Input
                          aria-label={`Plan ${i + 1} price`}
                          placeholder="Price"
                          value={plan.price}
                          onChange={(e) => updatePlan(i, "price", e.target.value)}
                          disabled={busy}
                          className="w-24"
                        />
                        <Input
                          aria-label={`Plan ${i + 1} period`}
                          placeholder="monthly / annual / one-time"
                          value={plan.period}
                          onChange={(e) => updatePlan(i, "period", e.target.value)}
                          disabled={busy}
                          className="w-48"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Remove plan ${i + 1}`}
                          onClick={() => removePlan(i)}
                          disabled={busy}
                        >
                          <X className="size-4" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      onClick={addPlan}
                      disabled={busy}
                    >
                      <Plus className="size-3" />
                      Add plan
                    </Button>
                  </div>
                </div>

                <div className="space-y-2 pt-1">
                  <Label htmlFor="fa-website">Links (all optional)</Label>
                  <Input
                    id="fa-website"
                    placeholder="Website URL — https://"
                    value={form.websiteUrl}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, websiteUrl: e.target.value }))
                    }
                    disabled={busy}
                  />
                  <Input
                    aria-label="GitHub URL"
                    placeholder="GitHub — https://github.com/owner/repo"
                    value={form.githubUrl}
                    onChange={(e) => setForm((f) => ({ ...f, githubUrl: e.target.value }))}
                    disabled={busy}
                  />
                  <Input
                    aria-label="App Store URL"
                    placeholder="App Store URL — https://apps.apple.com/…"
                    value={form.appStoreUrl}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, appStoreUrl: e.target.value }))
                    }
                    disabled={busy}
                  />
                  <Input
                    aria-label="Play Store URL"
                    placeholder="Play Store URL — https://play.google.com/…"
                    value={form.playStoreUrl}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, playStoreUrl: e.target.value }))
                    }
                    disabled={busy}
                  />
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    A link is what makes your app eligible for the archive. With none, it can
                    be compared but never published.
                  </p>
                </div>

                <div className="flex justify-end pt-1">
                  <Button type="submit" disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Draft from form
                  </Button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="agent">
              <form onSubmit={submitAgent} className="space-y-3 pt-3">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Label>Copy-paste prompt for your agent</Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      onClick={copyPrompt}
                      disabled={busy}
                    >
                      <ClipboardCopy className="size-3" />
                      Copy prompt
                    </Button>
                  </div>
                  <pre
                    data-lenis-prevent
                    className="max-h-52 overflow-auto rounded-2xl border border-border/60 bg-muted/40 p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap"
                  >
                    {AGENT_PROMPT}
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="fa-agent">Paste the JSON your agent returned</Label>
                  <Textarea
                    id="fa-agent"
                    rows={6}
                    value={agentJson}
                    onChange={(e) => {
                      setAgentJson(e.target.value);
                      setError(null);
                    }}
                    disabled={busy}
                    spellCheck={false}
                    placeholder={'{ "name": "…", "features": ["…"] }'}
                    className="font-mono text-[12px]"
                  />
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Malformed JSON or an unrecognised key is refused with the server&apos;s own
                    message — nothing is silently dropped.
                  </p>
                </div>

                <div className="flex justify-end pt-1">
                  <Button type="submit" disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Draft from JSON
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </>
  );
}

export function FounderAppDialog({
  open,
  onOpenChange,
  onCommitted,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCommitted?: (draft: FounderAppDraft) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-lenis-prevent
        className="max-h-[85vh] overflow-y-auto sm:max-w-2xl"
      >
        <FounderAppWizard onCommitted={onCommitted} />
      </DialogContent>
    </Dialog>
  );
}
