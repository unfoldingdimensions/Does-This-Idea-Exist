export interface Startup {
  id: number;
  name: string;
  tagline: string | null;
  description: string | null;
  category: string | null;
  website_url: string | null;
  github_url: string | null;
  founded: string | null;
  stars: number | null;
  language: string | null;
  status: "active" | "pivoted" | "dead";
  verified: number;
  verified_at: string | null;
  last_checked: string | null;
  check_failures: number;
  source: string;
  created_at: string;
  updated_at: string;
  /**
   * WHERE the `founded` value came from (F-04): `llm` · `wayback` · `rdap` ·
   * `human` · `unknown`. An RDAP hit is a DOMAIN REGISTRATION date, not a
   * founding year (Notion is filed 2000-11-01, founded 2013), so the UI must
   * label an approximated date instead of printing "founded {year}". Optional
   * in the type because rows written before Phase 1 carry no value.
   */
  date_source?: string | null;
  /**
   * WHO admitted the row (scale-to-10k, 2026-09-18): `human` · `machine` ·
   * null for rows written before the column existed (legacy = human). The
   * trust copy must distinguish: "a human checked this" is only true when
   * this is NOT 'machine' — a funnel-admitted row says so instead.
   * Optional because the list endpoint omits fields the client never reads.
   */
  approval_source?: "human" | "machine" | null;
  /** Which stage admitted a machine row: `funnel:http` · `funnel:render`. */
  approved_by?: string | null;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface Stats {
  total: number;
  verified: number;
  dead: number;
  last_checked: string | null;
}

export interface VerifyResult {
  checked: number;
  ok: number;
  skipped: number;
  flagged: number;
  dead_flipped: string[];
  breakdown: { verified: number; unverified: number; dead: number };
  already_verified: { id: number; name: string; url: string }[];
  suggested: { id: number; name: string; url: string }[];
  failed_list: { id: number; name: string; url: string; reason: string }[];
}

export interface SuggestedStartup {
  id: number;
  name: string;
  website_url: string | null;
  github_url: string | null;
  category: string;
  last_checked: string | null;
  created_at: string;
  /** Which store the row came from: an archive entry, or a founder's pending
   * publish request riding the same queue (F-24). The two MUST be decided
   * through different endpoints — an archive approve posts to
   * /api/admin/verify/approve (startups table), a submission to
   * /api/admin/founder/submissions/{id}/approve|reject. Default "archive"
   * because rows from an older backend carry no tag. */
  kind?: "archive" | "founder_submission";
  submission_id?: number;
  founder_app_id?: number;
}

export interface VerifyJob {
  id: string;
  kind: string;
  source: string;
  status: "queued" | "running" | "done" | "failed";
  queue_position: number | null;
  total: number;
  done: number;
  ok: number;
  skipped: number;
  failed: number;
  errors: string[];
  current: string;
  breakdown: { verified: number; unverified: number; dead: number };
  result: VerifyResult | null;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
}

// --- Teardown, trust and the two stores (Phases 1-3, consumed by Phase 6) ---

/**
 * The nullable teardown columns Phases 1-2 added to every archive row.
 * Canonical names: `docs/teardown-spec.md` §5.1.
 */
export interface TeardownColumns {
  entity_type: string | null;
  canonical_domain: string | null;
  aliases: string | null;
  problem_statement: string | null;
  target_users: string | null;
  product_url: string | null;
  docs_url: string | null;
  demo_url: string | null;
  app_store_url: string | null;
  play_store_url: string | null;
  pricing_json: string | null;
  pricing_captured_at: string | null;
  pricing_source_url: string | null;
  features_json: string | null;
  positioning: string | null;
  content_notes: string | null;
  activity_checked_at: string | null;
  activity_summary: string | null;
  last_human_reviewed_at: string | null;
  review_notes: string | null;
  provenance: string | null;
}

/**
 * One claim, with the page it came from (F-02). `source_url` and `captured_at`
 * are NOT NULL in the database: evidence without a source is not evidence.
 * The closed vocabulary is `docs/teardown-spec.md` §5.1.
 */
export interface EvidenceRow {
  id: number;
  startup_id: number;
  evidence_type:
    | "feature"
    | "pricing"
    | "positioning"
    | "negative"
    | "review"
    | "repo_created"
    | "homepage_claim"
    | "wayback_first"
    | "reachability"
    | "curator_confirmation";
  source_url: string;
  captured_at: string;
  claim: string | null;
  value: string | null;
  provenance: string | null;
  confidence: number | null;
  reviewed_at: string | null;
}

/**
 * The two trust signals as EXPLICIT fields (F-21), never inferred client-side
 * from a raw timestamp. They describe the RECORD: a badge never sits next to a
 * claim (`docs/teardown-spec.md` §8.1).
 */
export interface BadgeFields {
  admin_verified: boolean;
  admin_verified_at: string | null;
  machine_verified: boolean;
  machine_verified_at: string | null;
  /**
   * Who admitted the row: 'human' | 'machine', or null for rows admitted before
   * 2026-09-18 (all of which were human). `admin_verified` is false whenever this
   * is 'machine', because a robot did not confirm the business - it reached it.
   */
  approval_source?: "human" | "machine" | null;
  /** Which gate admitted it: 'admin' | 'funnel:http' | 'funnel:render'. */
  approved_by?: string | null;
}

/** One pricing plan, as the founder or a capture entered it. */
export interface PricingPlan {
  name: string;
  price: string;
  period: string;
}

/** `pricing_json`, parsed. An uncaptured record is `{}` — not a zero. */
export interface Pricing {
  free_tier?: string;
  plans?: PricingPlan[];
}

/** A row of the archive as the API actually returns it (all 40 columns). */
export type ArchiveRow = Startup & TeardownColumns;

/**
 * `GET /api/startups/{slug}` — the archive row plus the slug it resolved as,
 * the two badges, the duplicate group, and the record's evidence rows (the
 * dossier's sourced "doesn't do" list reads those, never a stored column).
 */
export interface StartupRecord extends ArchiveRow, BadgeFields {
  slug: string;
  resolved_id: number;
  resolved_name: string;
  duplicate_group: { id: number; name: string; verified: boolean }[];
  /** Always a list. An uncaptured record answers `[]`, never a missing key. */
  evidence: EvidenceRow[];
}

/** `GET /api/search` — an archive row with the server's frozen match reason. */
export type SearchResult = ArchiveRow & { reason: string };

// --- The gap table (Phase 3) ------------------------------------------------

/**
 * Four bands, and `unknown` is one of them: missing data is SHOWN, never
 * scored, ranked or guessed (`docs/gap-table-format.md` §3). `asked_for` is the
 * demand group (dimension 7), outside the three comparison bands.
 */
export type GapBand =
  | "you_have_they_dont"
  | "they_have_you_dont"
  | "both_have"
  | "unknown"
  | "asked_for";

/** Exactly `{dimension, band, you, them, source, captured_at}`. */
export interface GapRow {
  dimension: string;
  band: GapBand;
  you: string;
  them: string;
  source: string;
  captured_at: string;
}

/** One competitor's summary as the table reports it. */
export interface GapCompetitor {
  id: number;
  name: string;
  slug: string;
  website_url?: string;
  has_teardown?: boolean;
}

export interface GapTable {
  you: { name: string; founder_app_id: number; profile: Record<string, unknown> };
  them: GapCompetitor[];
  competitors: { id: number; name: string; slug: string }[];
  groups: Record<GapBand, GapRow[]>;
  rows: GapRow[];
  bands: GapBand[];
  dimensions: string[];
}

/**
 * The capture-pending answer (F-22): a competitor's teardown is being captured,
 * so there is no table yet. Retry — never render a partial table as the answer.
 */
export interface CompareCapturePending {
  state: "queued" | "in_progress";
  message?: string | null;
  startup_id?: number;
  you: { founder_app_id: number; name: string };
  competitors: { id: number; name: string }[];
}

/** Non-happy compare answers, narrowed by the caller. */
export type CompareResult = GapTable | CompareCapturePending;

export function isCapturePending(r: CompareResult): r is CompareCapturePending {
  return (r as CompareCapturePending).state === "queued"
    || (r as CompareCapturePending).state === "in_progress";
}

// --- The founder's own store (F-10..F-13, F-20) -----------------------------

export type ArchiveStatus = "local_only" | "pending" | "approved" | "rejected" | "withdrawn";

/** What the founder entered or their agent produced — the "you" side. */
export interface FounderProfile {
  name: string;
  tagline: string | null;
  description: string | null;
  category: string | null;
  website_url: string | null;
  github_url: string | null;
  app_store_url: string | null;
  play_store_url: string | null;
  features: string[];
  pricing: Pricing;
  pricing_captured_at?: string | null;
  positioning: string | null;
  target_users: string | null;
}

/** The eligibility gate (F-20) — a real link, or comparison only. */
export interface Eligibility {
  has_link: boolean;
  link: string;
  link_field: "website_url" | "github_url" | "app_store_url" | "play_store_url" | null;
}

export interface FounderSubmission {
  id: number;
  founder_app_id: number;
  submitted_at: string;
  status: "pending" | "approved" | "rejected" | "withdrawn";
  archive_startup_id: number | null;
  decided_at: string | null;
  decided_by: string | null;
  /** The rejection reason, shown to the founder — with no accounts this is the
   * entire feedback loop. */
  note: string | null;
}

/** The draft response (`POST /api/founder-app`, `/confirm`, `/publish`). */
export interface FounderAppDraft {
  founder_app_id: number;
  profile: FounderProfile;
  confirmed: boolean;
  source_kind: "url" | "form" | "agent_json" | null;
  eligibility: Eligibility;
  publish_offered: boolean;
  archive_status: ArchiveStatus;
  submission: FounderSubmission | null;
  /** Per-draft secret, present ONLY on the creation response. The client stores
   * it (sessionStorage) and sends it back as X-Founder-Token — reads, confirms
   * and publishes never return it again. */
  founder_token?: string;
}

/** `GET /api/founder-app/{id}` — the draft plus the decision history. */
export interface FounderAppDetail extends FounderAppDraft {
  submissions: FounderSubmission[];
}

/**
 * `POST /api/founder-app/{id}/publish` — and it is deliberately NOT a draft.
 *
 * The route answers with an acknowledgement of the submission it just queued, not
 * with the record: `{submitted, submission_id, archive_status, message}`. Typing it
 * as `FounderAppDraft` would promise a `profile` the response does not carry, so the
 * caller re-reads `GET /api/founder-app/{id}` for the authoritative state and uses
 * this only for the immediate nudge. (The dialog was written defensively against
 * the narrower payload already; this makes the type tell the truth about it.)
 */
export interface FounderPublishResult {
  submitted: boolean;
  submission_id: number;
  archive_status: ArchiveStatus;
  message: string;
}

/** The form path's payload — features are REQUIRED, 5–10. */
export interface FounderFormInput {
  name: string;
  description?: string;
  target_user?: string;
  category?: string;
  features: string[];
  positioning?: string;
  pricing?: { free_tier?: string; plans?: PricingPlan[] };
  website_url?: string;
  github_url?: string;
  app_store_url?: string;
  play_store_url?: string;
}

// --- LLM gateways (docs/llm-gateways.md §3) --------------------------------

export type KeySource = "settings" | "env" | "none";

/** One gateway as the admin panel sees it. No response ever carries the key. */
export interface LlmGateway {
  id: string;
  label: string;
  default_base_url: string;
  default_model: string;
  suggested_models: string[];
  docs_url: string;
  notes: string;
  env_vars: string[];
  base_url: string;
  model: string;
  has_key: boolean;
  key_source: KeySource;
  /** Last 4 characters, e.g. `…cdef`; short keys report the literal `set`. */
  key_hint: string;
  /** `has_key && model` — the same condition the switch guard enforces. */
  ready: boolean;
  is_active: boolean;
  overrides: { api_key: boolean; model: boolean; base_url: boolean };
}

/** `GET /api/admin/settings/gateways` — the whole panel state in one call. */
export interface LlmGatewaysView {
  active: string;
  effective: {
    gateway_id: string;
    label: string;
    base_url: string;
    model: string;
    has_key: boolean;
    key_source: KeySource;
    ready: boolean;
  };
  gateways: LlmGateway[];
}

/** `PUT` body. An omitted field is left alone; `null`/`""` clears the override. */
export interface LlmGatewayPatch {
  api_key?: string | null;
  model?: string | null;
  base_url?: string | null;
}

/** `POST /api/admin/settings/gateways/{id}/test` — always 200 unless unknown. */
export interface LlmGatewayTestResult {
  ok: boolean;
  gateway_id: string;
  label: string;
  model: string;
  base_url: string;
  latency_ms: number;
  http_status?: number;
  reply?: string;
  model_echoed?: string;
  /** The provider's own text — a wrong model and a bad key are told apart by it. */
  error?: string;
}

export interface SeedJob {
  id: string;
  kind: "seed" | "verify";
  source: string;
  status: "queued" | "running" | "done" | "failed";
  queue_position: number | null;
  total: number;
  done: number;
  ok: number;
  skipped: number;
  failed: number;
  errors: string[];
  ok_urls: string[];
  skipped_urls: string[];
  current: string;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  /** Verify jobs carry their full result (buckets etc.) once terminal. */
  result: VerifyResult | null;
}
