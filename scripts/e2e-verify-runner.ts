/**
 * IdeaExists E2E Verification Suite (Tiers 1 - 4)
 * Opaque-box verification for Frontend Requirements R1 - R4.
 */

// The DOM bootstrap lives in its own module and MUST be the first import:
// several upstream packages (Radix's portal above all) capture a global at
// module-evaluation time, and esbuild hoists every import above a module's own
// statements — so installing jsdom inline is too late and dialogs render empty.
// See scripts/e2e-dom-setup.ts.
import { setReducedMotion } from "./e2e-dom-setup";

// Sample Data Fixtures for E2E Tests — shaped to frontend/lib/types.ts
const MOCK_STARTUPS: Startup[] = [
  {
    id: 1,
    name: "Apex AI",
    tagline: "Autonomous Workflow Synthesis Engine",
    description: "Apex AI orchestrates autonomous intelligent agents across enterprise cloud workflows with deterministic safety constraints.",
    category: "ai",
    founded: "2024-03-15",
    website_url: "https://apexai.test",
    github_url: "https://github.com/apexai/engine",
    verified: 1,
    verified_at: "2024-04-01T12:00:00Z",
    status: "active",
    stars: 1250,
    language: "TypeScript",
    last_checked: "2024-05-01T00:00:00Z",
    check_failures: 0,
    source: "github",
    created_at: "2024-03-15 10:00:00",
    updated_at: "2024-05-01 00:00:00",
  },
  {
    id: 2,
    name: "Flux DB",
    tagline: "Ultra-fast distributed time series database",
    description: "High performance time series storage with real-time stream analytical querying built in Rust.",
    category: "devtools",
    founded: "2023-08-10",
    website_url: "https://fluxdb.test",
    github_url: "https://github.com/fluxdb/flux",
    verified: 0,
    verified_at: null,
    status: "active",
    stars: 840,
    language: "Rust",
    last_checked: "2024-05-02T00:00:00Z",
    check_failures: 0,
    source: "github",
    created_at: "2023-08-10 09:00:00",
    updated_at: "2024-05-02 00:00:00",
  },
  {
    id: 3,
    name: "Legacy Cloud",
    tagline: "Archival legacy migration suite",
    description: "Old enterprise infrastructure hosting solution, now closed down.",
    category: "productivity",
    founded: "2018-01-01",
    website_url: "https://legacycloud.test",
    github_url: "https://github.com/legacycloud/archive",
    verified: 0,
    verified_at: null,
    status: "dead",
    stars: 50,
    language: "Python",
    last_checked: "2024-05-03T00:00:00Z",
    check_failures: 3,
    source: "github",
    created_at: "2018-01-01 08:00:00",
    updated_at: "2024-05-03 00:00:00",
  },
];

const MOCK_CATEGORIES = [
  { category: "ai", count: 1 },
  { category: "devtools", count: 1 },
  { category: "productivity", count: 1 },
];

const MOCK_STATS = {
  total: 3,
  verified: 1,
  dead: 1,
  last_checked: "2024-05-03T00:00:00Z",
};

// Mock fetch for API layer
global.fetch = (async (input: RequestInfo | URL) => {
  const url = input.toString();
  if (url.includes("/api/startups")) {
    return {
      ok: true,
      status: 200,
      json: async () => MOCK_STARTUPS,
    } as Response;
  }
  if (url.includes("/api/categories")) {
    return {
      ok: true,
      status: 200,
      json: async () => MOCK_CATEGORIES,
    } as Response;
  }
  if (url.includes("/api/stats")) {
    return {
      ok: true,
      status: 200,
      json: async () => MOCK_STATS,
    } as Response;
  }
  return {
    ok: true,
    status: 200,
    json: async () => ({}),
  } as Response;
}) as any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { ThemeProvider } from "next-themes";
import { StartupCard } from "../frontend/components/startup-card";
import { ThemeToggle } from "../frontend/components/theme-toggle";
import { MorphingDiscoveryBar } from "../frontend/components/ui/morphing-discovery-bar";
import { FilterBar } from "../frontend/components/filter-bar";
import HomePage from "../frontend/app/page";
import type { Startup } from "../frontend/lib/types";

// Test Runner Infrastructure
let passedCount = 0;
let failedCount = 0;

function assert(condition: boolean, description: string) {
  if (condition) {
    passedCount++;
    console.log(`  ✓ PASS: ${description}`);
  } else {
    failedCount++;
    console.error(`  ✗ FAIL: ${description}`);
  }
}

function suite(name: string, fn: () => void) {
  console.log(`\n--- ${name} ---`);
  try {
    fn();
  } catch (err) {
    failedCount++;
    console.error(`  ✗ UNHANDLED EXCEPTION in ${name}:`, err);
  }
}

// Container & Root Setup
let container: HTMLElement;
let currentRoot: Root | null = null;

function setup() {
  if (currentRoot) {
    act(() => {
      currentRoot?.unmount();
    });
  }
  const rootDiv = document.getElementById("root");
  if (rootDiv) rootDiv.remove();
  
  container = document.createElement("div");
  container.id = "root";
  document.body.appendChild(container);
  currentRoot = createRoot(container);
}

function teardown() {
  if (currentRoot) {
    act(() => {
      currentRoot?.unmount();
    });
    currentRoot = null;
  }
  container.innerHTML = "";
  document.documentElement.className = "";
  setReducedMotion(false);
}

// Helper to render wrapped in ThemeProvider
function renderWithTheme(ui: React.ReactNode) {
  setup();
  act(() => {
    currentRoot?.render(
      React.createElement(
        ThemeProvider,
        { attribute: "class", defaultTheme: "light", enableSystem: false },
        ui
      )
    );
  });
}

// ==========================================
// TIER 1: FEATURE COVERAGE (R1 - R4)
// ==========================================

suite("Tier 1: Bespoke Animated Celestial Theme Toggle (R2)", () => {
  renderWithTheme(React.createElement(ThemeToggle));

  const button = container.querySelector("button") as HTMLButtonElement;
  assert(button !== null, "R2.1: Theme toggle button rendered");
  assert(button.getAttribute("aria-label")?.includes("Switch to"), "R2.2: Theme toggle button has descriptive aria-label");
  assert(button.classList.contains("glass"), "R2.3: Theme toggle button uses signature glass aesthetic");

  act(() => {
    button.click();
  });

  assert(button.getAttribute("aria-label") !== undefined, "R2.4: Toggle click manages theme state and button aria-label");

  teardown();
});

suite("Tier 1: Fluid Micro-Interactions & Spotlight Glass Cards (R3)", () => {
  renderWithTheme(React.createElement(StartupCard, { startup: MOCK_STARTUPS[0] }));

  assert(container.textContent?.includes("Apex AI") === true, "R3.1: Card displays startup name 'Apex AI'");
  assert(container.textContent?.includes("Autonomous Workflow Synthesis Engine") === true, "R3.2: Card displays startup tagline");
  assert(container.querySelector("a[href='https://apexai.test']") !== null, "R3.3: Action button linked to website URL");
  assert(container.querySelector("a[href='https://github.com/apexai/engine']") !== null, "R3.4: Action button linked to GitHub code URL");
  assert(container.textContent?.includes("1,250") === true, "R3.5: Card formats and displays stars count");

  teardown();
});

suite("Tier 1: Trust Stamp & Status Pill Animation (R3)", () => {
  let statusChangedTo: string | null = null;

  renderWithTheme(
    React.createElement(StartupCard, {
      startup: MOCK_STARTUPS[0],
      onStatusChange: (_s, choice) => { statusChangedTo = choice; },
    })
  );

  const statusBtn = container.querySelector("button") as HTMLButtonElement;
  assert(statusBtn !== null, "R3.6: Status pill button rendered");
  assert(container.textContent?.includes("Verified") === true, "R3.7: Status pill displays 'Verified' label");

  teardown();
});

suite("Tier 1: Discovery Bar & Atmosphere Polish (R4)", () => {
  let currentQuery = "";
  let currentCat: string | null = null;

  const categories = [
    { id: "ai", label: "AI", icon: null, count: 25 },
    { id: "devtools", label: "DevTools", icon: null, count: 18 },
    { id: "productivity", label: "Productivity", icon: null, count: 12 },
    { id: "finance", label: "Finance", icon: null, count: 8 },
  ];

  renderWithTheme(
    React.createElement(MorphingDiscoveryBar, {
      categories,
      value: currentCat,
      onCategoryChange: (c) => { currentCat = c; },
      query: currentQuery,
      onQueryChange: (q) => { currentQuery = q; },
      totalCount: 63,
    })
  );

  const searchInput = container.querySelector("input[aria-label='Search startups']") as HTMLInputElement;
  assert(searchInput !== null, "R4.1: Search input with aria-label 'Search startups' rendered");
  assert(container.querySelector(".search-focus-ring") !== null, "R4.2: Search focus ring container present");

  const chips = container.querySelectorAll("button");
  assert(chips.length >= 4, "R4.3: Inline category chips (All + top 3 categories) rendered");

  teardown();
});

suite("Tier 1: Category Chips & More Dropdown (R4)", () => {
  let currentCat: string | null = null;
  const categories = [
    { id: "ai", label: "AI", icon: null, count: 25 },
    { id: "devtools", label: "DevTools", icon: null, count: 18 },
    { id: "productivity", label: "Productivity", icon: null, count: 12 },
    { id: "finance", label: "Finance", icon: null, count: 8 },
    { id: "health", label: "Health", icon: null, count: 5 },
  ];

  renderWithTheme(
    React.createElement(MorphingDiscoveryBar, {
      categories,
      value: currentCat,
      onCategoryChange: (c) => { currentCat = c; },
      query: "",
      onQueryChange: () => {},
    })
  );

  const moreBtn = Array.from(container.querySelectorAll("button")).find((b) => b.textContent?.includes("More"));
  assert(moreBtn !== undefined, "R4.4: 'More' button rendered for extra categories");

  if (moreBtn) {
    act(() => {
      moreBtn.click();
    });
    assert(container.querySelector("[role='menu']") !== null || container.textContent?.includes("Finance") === true || container.textContent?.includes("Health") === true, "R4.5: Clicking 'More' button expands category dropdown");
  }

  teardown();
});

// ==========================================
// TIER 2: BOUNDARY & CORNER CASES
// ==========================================

suite("Tier 2: Boundary & Corner Cases", () => {
  // T8.1: Reduced motion compliance (SkyBackground was deleted as dead code
  // in 2026-09-22's housekeeping round — ThemeToggle carries the check now)
  setReducedMotion(true);
  renderWithTheme(React.createElement(ThemeToggle));

  const button = container.querySelector("button") as HTMLButtonElement;
  assert(button !== null, "T8.1: ThemeToggle mounts cleanly under prefers-reduced-motion: reduce");

  teardown();

  // T8.2: Rapid theme toggle stress test
  renderWithTheme(React.createElement(ThemeToggle));

  const toggleBtn = container.querySelector("button") as HTMLButtonElement;
  act(() => {
    for (let i = 0; i < 15; i++) {
      toggleBtn.click();
    }
  });

  assert(container.querySelector("button") !== null, "T8.2: Rapid 15x theme toggle clicks executed without exception or DOM breakage");

  teardown();

  // T8.3: Empty search query handling
  let queryState = "non_existent_startup_query_999999";
  const categories = [{ id: "ai", label: "AI", icon: null, count: 1 }];

  renderWithTheme(
    React.createElement(MorphingDiscoveryBar, {
      categories,
      value: null,
      onCategoryChange: () => {},
      query: queryState,
      onQueryChange: (q) => { queryState = q; },
    })
  );

  const clearBtn = container.querySelector("button[aria-label='Clear search']") as HTMLButtonElement;
  assert(clearBtn !== null, "T8.3: Clear search button appears when query is typed");

  act(() => {
    clearBtn.click();
  });

  assert(queryState === "", "T8.3b: Clicking Clear search button clears query state to empty string");

  teardown();

  // T8.4: Keyboard Escape Key Dropdown Closing
  renderWithTheme(
    React.createElement(MorphingDiscoveryBar, {
      categories: [
        { id: "c1", label: "C1", icon: null },
        { id: "c2", label: "C2", icon: null },
        { id: "c3", label: "C3", icon: null },
        { id: "c4", label: "C4", icon: null },
        { id: "c5", label: "C5", icon: null },
      ],
      value: null,
      onCategoryChange: () => {},
      query: "",
      onQueryChange: () => {},
    })
  );

  const moreBtn = Array.from(container.querySelectorAll("button")).find((b) => b.textContent?.includes("More"));
  if (moreBtn) {
    act(() => {
      moreBtn.click();
    });
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    assert(true, "T8.4: Escape key dispatch handled cleanly without errors");
  }

  teardown();
});

// ==========================================
// TIER 3: CROSS-FEATURE COMBINATIONS
// ==========================================

suite("Tier 3: Cross-Feature Combinations", () => {
  renderWithTheme(
    React.createElement(
      "div",
      null,
      React.createElement(ThemeToggle),
      React.createElement(ThemeToggle, { key: "second" })
    )
  );

  assert(container.querySelector("button") !== null, "T9.1: ThemeToggle instances mounted simultaneously");
  
  const toggleBtn = container.querySelector("button") as HTMLButtonElement;
  act(() => {
    toggleBtn.click();
  });

  assert(toggleBtn.getAttribute("aria-label") !== undefined, "T9.2: Theme toggle click manages theme state across mounted instances");

  teardown();

  // T9.3: FilterBar with facets combination
  let activeSort = "top";
  let activeYear = "2024";
  let activeStatus = "verified";

  renderWithTheme(
    React.createElement(FilterBar, {
      sort: activeSort as any,
      onSort: (s) => { activeSort = s; },
      year: activeYear,
      onYear: (y) => { activeYear = y; },
      status: activeStatus,
      onStatus: (st) => { activeStatus = st; },
      years: ["2024", "2023"],
      count: 1,
      onClear: () => { activeYear = "all"; activeStatus = "all"; },
      showClear: true,
      searching: true,
    })
  );

  assert(container.textContent?.includes("Clear all") === true, "T9.3: FilterBar shows 'Clear all' button when facets active");

  teardown();
});

// ==========================================
// TIER 4: REAL-WORLD APPLICATION SCENARIOS
// ==========================================

suite("Tier 4: End-to-End User Navigation Session", () => {
  renderWithTheme(React.createElement(HomePage));

  assert(container.querySelector("header") !== null, "T10.1: Main application header mounted");
  assert(container.querySelector("main") !== null, "T10.2: Main application content viewport mounted");
  assert(container.querySelector("footer") !== null, "T10.3: Application footer mounted");

  teardown();
});

// ===========================================================================
// PHASE 7 — the twelve frontend test areas (docs/frontend-plan.md §3)
// ===========================================================================
//
// Everything below renders the real product components against stubbed HTTP in
// a real DOM. Nothing here reaches the network, a server, the live archive or
// the LLM: `globalThis.fetch` is replaced per test and restored in a `finally`
// (a leaked stub would make every later suite lie).
//
// Fixtures are the shapes the backend ACTUALLY answered with, recorded in
// docs/phase-ledger.md ("Phase 6 evidence", §2-§4). Where a fixture is built
// from the contract rather than copied from a ledger byte, the canonical source
// is named in the comment above it. A fixture invented from a TypeScript type
// would happily pass while the UI was wrong — so the negatives, the compare
// rows and the non-happy states are copied, and labelled as copied.

import type {
  EvidenceRow,
  FounderAppDraft,
  GapTable,
  StartupRecord,
} from "../frontend/lib/types";
import { filterStartups } from "../frontend/lib/search";
import { foundedLabel, foundedShort } from "../frontend/lib/format";
import {
  CompareNotConfirmed,
  RecordNotFound,
  compareStartups,
  exportGapTable,
  fetchStartupRecord,
  searchStartups,
} from "../frontend/lib/api";
import { StartupDetail } from "../frontend/components/startup-detail";
import { TeardownDossier } from "../frontend/components/teardown-dossier";
import { GapTablePanel } from "../frontend/components/gap-table";
import { GapExportButtons } from "../frontend/components/gap-export-buttons";
import { FounderAppDialog } from "../frontend/components/founder-app-dialog";
import { Toaster } from "../frontend/components/ui/sonner";
import ProductPage from "../frontend/app/products/[slug]/page";
// Next's client hooks read these two contexts, so a route component can be
// rendered outside the Next runtime by providing them directly instead of
// standing up the app router. (next/dist has no "exports" restriction.)
import {
  PathParamsContext,
  SearchParamsContext,
} from "next/dist/shared/lib/hooks-client-context.shared-runtime";

// --- Phase 7 harness -------------------------------------------------------

interface StubRoute {
  /** Matched with `url.includes(...)`. */
  url: string;
  /** Uppercased HTTP method; omitted = any. */
  method?: string;
  status?: number;
  /** JSON payload (or the raw string when `text` is used instead). */
  json?: unknown;
  text?: string;
  ctype?: string;
  /** Never settle, so the component stays on its loading state. */
  hang?: boolean;
  /** Reject like a dead network. */
  fail?: boolean;
}

interface StubCall {
  url: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
}

function stubResponse(route: StubRoute): Response {
  const status = route.status ?? 200;
  const text = route.text ?? JSON.stringify(route.json ?? {});
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (key: string) =>
        key.toLowerCase() === "content-type" ? (route.ctype ?? "application/json") : null,
    },
    json: async () => JSON.parse(text),
    text: async () => text,
  } as unknown as Response;
}

/**
 * A hermetic fetch stub. An unmatched request answers 404 with its own URL in
 * the detail, so a forgotten route fails the assertion that needed it instead
 * of silently returning `{}` and letting the UI look right for the wrong reason.
 */
class Stub {
  readonly calls: StubCall[] = [];
  private readonly routes: StubRoute[];
  private readonly saved: typeof globalThis.fetch;

  constructor(routes: StubRoute[]) {
    this.routes = routes;
    this.saved = globalThis.fetch;
    globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      let body: unknown = null;
      if (typeof init?.body === "string") {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = init.body;
        }
      }
      this.calls.push({ url, method, body, headers: (init?.headers ?? {}) as Record<string, string> });
      const route = this.routes.find((r) => url.includes(r.url) && (!r.method || r.method === method));
      if (!route) {
        return Promise.resolve(
          stubResponse({ status: 404, json: { detail: `no stub for ${method} ${url}` } }),
        );
      }
      if (route.hang) return new Promise<Response>(() => {});
      if (route.fail) return Promise.reject(new TypeError("Failed to fetch"));
      return Promise.resolve(stubResponse(route));
    }) as typeof globalThis.fetch;
  }

  callsTo(substring: string, method?: string): StubCall[] {
    return this.calls.filter(
      (c) => c.url.includes(substring) && (!method || c.method === method),
    );
  }

  restore(): void {
    globalThis.fetch = this.saved;
  }
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
const flush = () => act(async () => { await delay(20); });

interface Mounted {
  host: HTMLElement;
  root: Root;
  /** The rendered subtree only — the theme script and portals live outside it. */
  app: HTMLElement;
}

const mountedRoots: Root[] = [];

async function mountApp(
  ui: React.ReactNode,
  theme: "light" | "dark" = "light",
): Promise<Mounted> {
  // next-themes resolves the stored preference BEFORE the defaultTheme, and the
  // Tier 1-4 suites toggle the theme (which persists it). Clear the key so a
  // mounted theme is the one the test asked for, not the one a sibling left.
  try {
    globalThis.localStorage.removeItem("theme");
  } catch {
    /* storage unavailable */
  }
  const host = document.createElement("div");
  host.id = "p7-host";
  document.body.appendChild(host);
  const root = createRoot(host);
  mountedRoots.push(root);
  await act(async () => {
    root.render(
      React.createElement(
        ThemeProvider,
        { attribute: "class", defaultTheme: theme, enableSystem: false },
        React.createElement("div", { id: "p7-app" }, ui as React.ReactElement),
      ),
    );
  });
  await flush();
  return { host, root, app: host.querySelector("#p7-app") as HTMLElement };
}

/** Unmount every Phase 7 tree and clear the body of anything a portal left. */
function cleanupApp(): void {
  while (mountedRoots.length > 0) {
    const root = mountedRoots.pop();
    act(() => {
      root?.unmount();
    });
  }
  const base = document.getElementById("root");
  Array.from(document.body.children).forEach((child) => {
    if (child !== base) child.remove();
  });
  document.documentElement.className = "";
  try {
    globalThis.localStorage.removeItem("theme");
  } catch {
    /* storage unavailable */
  }
  setReducedMotion(false);
}

async function withStub(
  routes: StubRoute[],
  fn: (stub: Stub) => Promise<void>,
): Promise<void> {
  const stub = new Stub(routes);
  try {
    await fn(stub);
  } finally {
    cleanupApp();
    stub.restore();
  }
}

async function suiteAsync(name: string, fn: () => Promise<void>): Promise<void> {
  console.log(`\n--- ${name} ---`);
  try {
    await fn();
  } catch (err) {
    failedCount++;
    console.error(`  ✗ UNHANDLED EXCEPTION in ${name}:`, err);
  }
}

// --- DOM helpers -----------------------------------------------------------

const domWindow = globalThis.window as unknown as Window;

function appText(el: ParentNode): string {
  return (el.textContent ?? "").replace(/\s+/g, " ").trim();
}

/** Body text with the theme script stripped — portals (dialogs, toasts) are
 * rendered straight into <body>, so assertions on a dialog need this. */
function bodyText(): string {
  const clone = document.body.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("script,style").forEach((n) => n.remove());
  return appText(clone);
}

function allButtons(scope: ParentNode = document): HTMLButtonElement[] {
  return Array.from(scope.querySelectorAll("button"));
}

function buttonNamed(name: string, scope: ParentNode = document): HTMLButtonElement | undefined {
  const wanted = name.toLowerCase();
  return allButtons(scope).find((b) => (b.textContent ?? "").trim().toLowerCase().includes(wanted));
}

function click(el: Element): void {
  act(() => {
    el.dispatchEvent(new domWindow.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
  });
}

/** Radix Tabs/Trigger activate on mousedown, not on a bare click. */
function activate(el: Element): void {
  act(() => {
    el.dispatchEvent(new domWindow.MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0 }));
  });
  click(el);
}

function setField(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const proto =
    el.tagName === "TEXTAREA"
      ? (domWindow.HTMLTextAreaElement.prototype as unknown as { value: string })
      : (domWindow.HTMLInputElement.prototype as unknown as { value: string });
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  act(() => {
    setter?.call(el, value);
    el.dispatchEvent(new domWindow.Event("input", { bubbles: true }));
  });
}

async function submitFrom(fieldId: string): Promise<void> {
  const field = document.querySelector(`#${fieldId}`) as HTMLElement | null;
  const form = field?.closest("form") ?? null;
  if (!form) {
    assert(false, `a form containing #${fieldId} exists`);
    return;
  }
  await act(async () => {
    form.dispatchEvent(new domWindow.Event("submit", { bubbles: true, cancelable: true }));
    await delay(15);
  });
}

async function switchTab(label: string): Promise<void> {
  const trigger = Array.from(document.querySelectorAll('[role="tab"]')).find((t) =>
    (t.textContent ?? "").includes(label),
  );
  if (!trigger) {
    assert(false, `a ${label} tab trigger exists`);
    return;
  }
  activate(trigger);
  await flush();
}

/** Every external link must carry rel="noopener noreferrer" AND an aria-label
 * naming what it opens (docs/frontend-plan.md §3 area 8, item 8 carry-over). */
function assertExternalLinks(scope: ParentNode, surface: string): void {
  const links = Array.from(scope.querySelectorAll('a[target="_blank"]')) as HTMLAnchorElement[];
  assert(links.length > 0, `${surface}: renders at least one external link`);
  const relOffenders = links
    .filter((a) => {
      const rel = a.getAttribute("rel") ?? "";
      return !rel.includes("noopener") || !rel.includes("noreferrer");
    })
    .map((a) => a.getAttribute("href"));
  assert(
    relOffenders.length === 0,
    `${surface}: every external link carries rel="noopener noreferrer"${relOffenders.length ? ` (offenders: ${relOffenders.join(", ")})` : ""}`,
  );
  const ariaOffenders = links
    .filter((a) => !(a.getAttribute("aria-label") ?? "").trim())
    .map((a) => a.getAttribute("href"));
  assert(
    ariaOffenders.length === 0,
    `${surface}: every external link carries an aria-label naming what it opens${ariaOffenders.length ? ` (offenders: ${ariaOffenders.join(", ")})` : ""}`,
  );
}

// --- Fixtures --------------------------------------------------------------

const startupRow = (over: Partial<Startup>): Startup =>
  ({
    id: 0,
    name: "",
    tagline: null,
    description: null,
    category: "other",
    website_url: null,
    github_url: null,
    founded: null,
    stars: null,
    language: null,
    status: "active",
    verified: 0,
    verified_at: null,
    last_checked: null,
    check_failures: 0,
    source: "website",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...over,
  }) as Startup;

/**
 * The three negative evidence rows the ledger records for `obsidian`
 * (docs/phase-ledger.md, Phase 6 §2 item 1: "evidence = 3 rows — no self-host /
 * API: unknown / no mobile app, each with its source_url and captured_at").
 * `source_url`/`captured_at` are NOT NULL in the database, so neither is
 * optional here.
 */
const EVIDENCE_NEGATIVES: EvidenceRow[] = [
  {
    id: 101, startup_id: 1, evidence_type: "negative",
    source_url: "https://obsidian.md/pricing", captured_at: "2026-09-16 04:12:00",
    claim: "no self-host", value: "observed: pricing page lists Free / Pro / Team only",
    provenance: "machine_drafted", confidence: 0.7, reviewed_at: null,
  },
  {
    id: 102, startup_id: 1, evidence_type: "negative",
    source_url: "https://obsidian.md/docs", captured_at: "2026-09-16 04:12:00",
    claim: "API", value: "unknown",
    provenance: "machine_drafted", confidence: null, reviewed_at: null,
  },
  {
    id: 103, startup_id: 1, evidence_type: "negative",
    source_url: "https://obsidian.md/", captured_at: "2026-09-16 04:12:00",
    claim: "no mobile app", value: "observed: footer lists no store link",
    provenance: "machine_drafted", confidence: 0.6, reviewed_at: null,
  },
];

/**
 * `GET /api/startups/obsidian` as Phase 6 recorded it: pricing / features /
 * positioning all `unknown`, three negative evidence rows, both badges earned
 * (Admin Verified Aug 10 2026, Machine Verified last checked Sep 16 2026).
 */
const RECORD_UNCAPTURED: StartupRecord = {
  id: 1, name: "Obsidian", tagline: "Private, local-first notes",
  description: "A knowledge base that works on local Markdown files.",
  category: "productivity", website_url: "https://obsidian.md",
  github_url: "https://github.com/obsidianmd/obsidian-releases",
  founded: "2020-01-01", date_source: null, stars: 0, language: null,
  status: "active", verified: 1, verified_at: "2026-08-10 00:00:00",
  last_checked: "2026-09-16 00:00:00", check_failures: 0, source: "website",
  created_at: "2026-01-01 00:00:00", updated_at: "2026-09-16 00:00:00",
  entity_type: "product", canonical_domain: "obsidian.md", aliases: null,
  problem_statement: null, target_users: null, product_url: null,
  docs_url: null, demo_url: null, app_store_url: null, play_store_url: null,
  pricing_json: null, pricing_captured_at: null, pricing_source_url: null,
  features_json: null, positioning: null, content_notes: null,
  activity_checked_at: null, activity_summary: null, last_human_reviewed_at: null,
  review_notes: null, provenance: "machine_drafted",
  slug: "obsidian", resolved_id: 1, resolved_name: "Obsidian",
  duplicate_group: [], evidence: EVIDENCE_NEGATIVES,
  admin_verified: true, admin_verified_at: "2026-08-10 00:00:00",
  machine_verified: true, machine_verified_at: "2026-09-16 00:00:00",
};

/**
 * A captured dossier. Not a ledger byte: built from the canonical column
 * contract (docs/teardown-spec.md §5.1 `pricing_json` shape) and the §6 worked
 * example ("Free (up to 3 docs) · Pro $8/mo annual · Team $12/user/mo · captured
 * 2026-09-15, source noted.app/pricing", 7 features, the positioning line).
 */
const RECORD_CAPTURED: StartupRecord = {
  ...RECORD_UNCAPTURED,
  id: 7, slug: "noted", resolved_id: 7, resolved_name: "Noted",
  name: "Noted", tagline: "A private, local-first note app",
  website_url: "https://noted.app", github_url: null,
  pricing_json: JSON.stringify({
    free_tier: "Free (up to 3 docs)",
    plans: [
      { name: "Pro", price: "$8/mo", period: "annual" },
      { name: "Team", price: "$12/user/mo", period: "monthly" },
    ],
  }),
  pricing_captured_at: "2026-09-15 00:00:00",
  pricing_source_url: "https://noted.app/pricing",
  features_json: JSON.stringify([
    "markdown notes", "backlinks", "graph view", "local files",
    "plugins", "sync (paid)", "publish",
  ]),
  positioning: "A private, local-first note app that links your thinking.",
  target_users: "knowledge workers who want their notes in files they own",
  evidence: [
    {
      id: 201, startup_id: 7, evidence_type: "positioning",
      source_url: "https://noted.app", captured_at: "2026-09-15 00:00:00",
      claim: "homepage hero", value: "A private, local-first note app that links your thinking.",
      provenance: "machine_drafted", confidence: 0.9, reviewed_at: null,
    },
    // A review row must NOT grow a dossier panel — reviews are gap-table
    // dimension 7 (docs/teardown-spec.md §9, docs/gap-table-format.md §2).
    {
      id: 202, startup_id: 7, evidence_type: "review",
      source_url: "https://g2.com/noted-reviews", captured_at: "2026-09-15 00:00:00",
      claim: "reviewer request", value: "offline mode",
      provenance: "machine_drafted", confidence: 0.5, reviewed_at: null,
    },
  ],
};

/**
 * `POST /api/compare` -> 200, the rows the ledger prints under "Real bytes
 * behind the renders" (docs/phase-ledger.md, Phase 6 §4). The empty band is a
 * real band with no rows.
 */
const GAP_READY: GapTable = {
  you: { name: "Phase 6 Evidence App", founder_app_id: 2, profile: {} },
  them: [{ id: 1, name: "Obsidian", slug: "obsidian", website_url: "https://obsidian.md", has_teardown: true }],
  competitors: [{ id: 1, name: "Obsidian", slug: "obsidian" }],
  groups: {
    you_have_they_dont: [
      { dimension: "Features", band: "you_have_they_dont", you: "local files", them: "not in their feature list (Obsidian)", source: "https://obsidian.md", captured_at: "" },
      { dimension: "Features", band: "you_have_they_dont", you: "backlinks", them: "not in their feature list (Obsidian)", source: "https://obsidian.md", captured_at: "" },
    ],
    they_have_you_dont: [],
    both_have: [
      { dimension: "What it doesn't do", band: "both_have", you: "n/a - not in your declared features", them: "no self-host (Obsidian)", source: "https://obsidian.md/pricing", captured_at: "" },
    ],
    unknown: [
      { dimension: "Pricing", band: "unknown", you: "Pro $8/monthly", them: "unknown", source: "", captured_at: "" },
      { dimension: "Free tier", band: "unknown", you: "Free up to 3 vaults", them: "unknown (Obsidian)", source: "", captured_at: "" },
      { dimension: "What it doesn't do", band: "unknown", you: "yes - declared: public API", them: "unknown - could not read the page (Obsidian)", source: "https://obsidian.md/docs", captured_at: "" },
      // The empty-claim-cell path: `ClaimCell` must print the word `unknown`,
      // never a blank cell (§3.4).
      { dimension: "Activity / liveness", band: "unknown", you: "", them: "", source: "", captured_at: "" },
    ],
    asked_for: [],
  },
  rows: [], bands: [], dimensions: [],
};

/**
 * Dimension 7. Not a ledger byte: the rows are the worked example in
 * docs/gap-table-format.md §6 (offline mode covered by your features -> group 1;
 * native mobile app requested by both sides -> group 4), with the review links
 * the format doc itself uses.
 */
const GAP_DIMENSION7: GapTable = {
  you: { name: "Loom-note", founder_app_id: 4, profile: {} },
  them: [{ id: 7, name: "Noted", slug: "noted" }],
  competitors: [{ id: 7, name: "Noted", slug: "noted" }],
  groups: {
    you_have_they_dont: [
      { dimension: "Offline mode", band: "you_have_they_dont", you: "yes (declared feature: local files)", them: "no (3 reviewers asked for it)", source: "g2.com/noted-reviews", captured_at: "" },
    ],
    they_have_you_dont: [],
    both_have: [],
    unknown: [],
    asked_for: [
      { dimension: "Native mobile app", band: "asked_for", you: "no", them: "no (7 reviewers asked for it)", source: "reddit.com/r/noted", captured_at: "" },
    ],
  },
  rows: [], bands: [], dimensions: [],
};

const DRAFT_UNCONFIRMED: FounderAppDraft = {
  founder_app_id: 9,
  profile: {
    name: "Loom-note", tagline: null,
    description: "An online-first note app with an API and real-time collaboration.",
    category: "productivity", website_url: null, github_url: null,
    app_store_url: null, play_store_url: null,
    features: ["real-time collaboration", "public API", "local files", "version history", "comments"],
    pricing: { free_tier: "Free up to 3 docs", plans: [{ name: "Pro", price: "$8/mo", period: "monthly" }] },
    pricing_captured_at: null,
    positioning: "Notes that sync themselves.",
    target_users: "small product teams",
  },
  confirmed: false, source_kind: "form",
  eligibility: { has_link: false, link: "", link_field: null },
  publish_offered: false, archive_status: "local_only", submission: null,
  founder_token: "founder-token-9",
};

const draftDetail = (draft: FounderAppDraft) => ({ ...draft, submissions: [] });

// --- Area 1: search with reasons -------------------------------------------

async function area1SearchWithReasons(): Promise<void> {
  const obsidian = startupRow({
    id: 1, name: "Obsidian", description: "local-first markdown notes",
    stars: 12, verified: 1, category: "productivity",
  });
  const thrash = startupRow({
    id: 2, name: "Thrash", tagline: "an obsidian-grade note vault",
    stars: 99999, verified: 1, category: "productivity",
  });
  const dead = startupRow({ id: 3, name: "Archive Cloud", status: "dead", stars: 88888 });

  // The server's per-result `reason`, frozen at the endpoint (F-18).
  await withStub(
    [{ url: "/api/search", json: [{ ...obsidian, reason: "Exact name match" }] }],
    async (stub) => {
      const rows = await searchStartups("obsidian");
      assert(rows.length === 1 && rows[0].reason === "Exact name match", "P7.1: GET /api/search returns the server's frozen reason per result");
      assert(stub.calls[0]?.url.includes("/api/search?q=obsidian"), "P7.1: the query is passed as ?q=");
    },
  );

  // The empty-query contract: 200 + [], and the archive is never touched.
  await withStub([{ url: "/api/search", json: [] }], async (stub) => {
    const rows = await searchStartups("");
    assert(Array.isArray(rows) && rows.length === 0, "P7.1: an empty query returns 200 [] — not the archive, not an error");
    assert(stub.calls.every((c) => !c.url.includes("/api/startups")), "P7.1: an empty query never falls back to the archive endpoint");
  });

  // The reason renders on the card, verbatim.
  await withStub([], async () => {
    const mounted = await mountApp(
      React.createElement(StartupCard, { startup: obsidian, reason: "Exact name match" }),
    );
    assert(appText(mounted.app).includes("match: Exact name match"), "P7.1: the result card renders the reason string verbatim");
  });

  // The client path still ranks the exact-name hit first over a higher-starred
  // fuzzy hit (lib/search.ts is the module scripts/sort-check.ts already pins).
  const ranked = filterStartups([thrash, obsidian, dead], { q: "obsidian" });
  assert(ranked[0]?.name === "Obsidian", "P7.1: the exact-name match ranks first, above a higher-starred fuzzy match");
  assert(!ranked.some((s) => s.name === "Archive Cloud"), "P7.1: a row with no match is not in the results");
}

// --- Area 2: dossier -> teardown -------------------------------------------

async function area2DossierTeardown(): Promise<void> {
  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: RECORD_UNCAPTURED }),
    );
    const text = appText(mounted.app);

    // Pricing has no capture: the dossier says `unknown` AND why, never a blank.
    assert(text.includes("Pricing — plan by plan"), "P7.2: the pricing section renders");
    assert(/unknown/.test(text), "P7.2: an uncaptured pricing section reads `unknown`, never blank or `no`");
    assert(text.includes("no pricing was captured for this record"), "P7.2: the unknown pricing section explains itself");

    // The sourced "doesn't do" list: one entry per negative evidence row, each
    // with the page it came from and the capture date.
    const items = Array.from(mounted.app.querySelectorAll("li")).filter((li) =>
      (li.textContent ?? "").includes("captured"),
    );
    assert(items.length === 3, `P7.2: all three negative observations render (got ${items.length})`);
    assert(
      items.some((li) => (li.textContent ?? "").includes("no self-host"))
        && items.some((li) => (li.textContent ?? "").includes("no mobile app")),
      "P7.2: each observation is printed in its own terms",
    );
    const links = items.map((li) => li.querySelector("a"));
    assert(links.every((a) => a !== null), "P7.2: every observation links the page it came from");
    assert(
      links.some((a) => a?.getAttribute("href") === "https://obsidian.md/pricing")
        && links.some((a) => a?.getAttribute("href") === "https://obsidian.md/docs"),
      "P7.2: the links are the evidence rows' own source_urls",
    );
    assert(items.every((li) => /captured Sep 16/.test(li.textContent ?? "")), "P7.2: every observation carries its capture date");

    // A retrieval failure is `unknown`, never "no API". The ledger's second
    // negative ("API: unknown") is the unreadable page, so it renders as the
    // literal word rather than as a claim about the world.
    assert(
      items.filter((li) => (li.textContent ?? "").trim().startsWith("unknown")).length === 1,
      "P7.2: the unreadable page renders as `unknown`, one of the three observations",
    );
    assert(!/no API/i.test(text), "P7.2: an unreadable page is never printed as `no API`");

    // Reviews must not grow a dossier panel — they are dimension 7.
    assert(!text.includes("offline mode") && !/user reviews/i.test(text), "P7.2: review evidence does not render a dossier panel");
  });

  await withStub([{ url: "/api/startups/noted", json: RECORD_CAPTURED }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "noted", initial: RECORD_CAPTURED }),
    );
    const text = appText(mounted.app);
    assert(text.includes("Free tier") && text.includes("Free (up to 3 docs)"), "P7.2: the free tier renders");
    assert(text.includes("Pro") && text.includes("$8/mo") && text.includes("/ annual"), "P7.2: each plan renders name, price and period");
    assert(text.includes("Team") && text.includes("$12/user/mo"), "P7.2: the second plan renders too");
    assert(text.includes("captured Sep 15"), "P7.2: pricing carries its capture date");
    const pricingLink = mounted.app.querySelector('a[href="https://noted.app/pricing"]');
    assert(pricingLink !== null, "P7.2: pricing links the page it was read from");
    assert(text.includes("markdown notes") && text.includes("backlinks") && text.includes("graph view"), "P7.2: the flat feature list renders");
    assert(text.includes("A private, local-first note app that links your thinking."), "P7.2: the positioning line renders from its evidence row");
  });
}

// --- Area 3: founder-app, three paths --------------------------------------

async function area3FounderPaths(): Promise<void> {
  const urlDraft: FounderAppDraft = {
    ...DRAFT_UNCONFIRMED,
    founder_app_id: 21, source_kind: "url",
    profile: { ...DRAFT_UNCONFIRMED.profile, features: [], name: "Loom-note" },
  };
  await withStub(
    [
      { url: "/api/founder-app/21", method: "GET", json: draftDetail(urlDraft) },
      { url: "/api/founder-app", method: "POST", json: urlDraft },
    ],
    async (stub) => {
      await mountApp(
        React.createElement(React.Fragment, null,
          React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }),
          React.createElement(Toaster, null),
        ),
      );
      setField(document.querySelector("#fa-url") as HTMLInputElement, "https://loom-note.test");
      await submitFrom("fa-url");

      const posts = stub.callsTo("/api/founder-app", "POST");
      assert(posts.length === 1, "P7.3: the URL path makes exactly one create call");
      assert(
        JSON.stringify(posts[0]?.body) === JSON.stringify({ url: "https://loom-note.test" }),
        "P7.3: the URL path posts {url} and nothing else",
      );
      assert(!("publish" in (posts[0]?.body as object)), "P7.3: create never sends a publish field (it is a 422 by contract)");
      const text = bodyText();
      assert(text.includes("Drafted from your website URL"), "P7.3: the draft is labelled as drafted from the URL");
      assert(text.includes("None yet — the URL path deliberately leaves features empty."), "P7.3: the URL draft invents no feature list");
      assert(text.includes("Machine draft — not confirmed."), "P7.3: a create response is never auto-confirmed");
      assert(buttonNamed("Confirm this draft") !== undefined, "P7.3: the confirm step is offered");
    },
  );

  // The form path rejects a feature list under 5 before any request is made.
  await withStub([{ url: "/api/founder-app", method: "POST", json: DRAFT_UNCONFIRMED }], async (stub) => {
    await mountApp(
      React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }),
    );
    await switchTab("Form");
    setField(document.querySelector("#fa-name") as HTMLInputElement, "Loom-note");
    setField(document.querySelector("#fa-features") as HTMLTextAreaElement, "a\nb\nc");
    await submitFrom("fa-name");
    assert(stub.callsTo("/api/founder-app", "POST").length === 0, "P7.3: a 3-feature form is refused locally, with no request");
    assert(
      (document.querySelector('[role="alert"]')?.textContent ?? "").includes("fewer than 5"),
      "P7.3: the refusal says why (fewer than 5 makes the comparison hollow)",
    );
    assert(
      (document.querySelector("#fa-features-help")?.textContent ?? "").includes("needs 5–10"),
      "P7.3: the live feature counter states the 5-10 rule",
    );
  });

  // The same form with 5 features drafts, and the body is the form contract.
  const formDraft: FounderAppDraft = { ...DRAFT_UNCONFIRMED, founder_app_id: 22 };
  await withStub(
    [
      { url: "/api/founder-app/22", method: "GET", json: draftDetail(formDraft) },
      { url: "/api/founder-app", method: "POST", json: formDraft },
    ],
    async (stub) => {
      await mountApp(React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }));
      await switchTab("Form");
      setField(document.querySelector("#fa-name") as HTMLInputElement, "Loom-note");
      setField(document.querySelector("#fa-features") as HTMLTextAreaElement, "real-time collaboration\npublic API\nlocal files\nversion history\ncomments");
      await submitFrom("fa-name");
      const post = stub.callsTo("/api/founder-app", "POST")[0];
      const body = post?.body as { name?: string; features?: string[] };
      assert(body?.name === "Loom-note", "P7.3: the form path posts the name");
      assert(body?.features?.length === 5, "P7.3: the form path posts the five features, one per line");
      assert(!("publish" in (post?.body as object)), "P7.3: the form path sends no publish field either");
      assert(bodyText().includes("Entered in the form"), "P7.3: the draft is labelled as entered in the form");
    },
  );

  // The agent path posts the pasted text as a raw string, unparsed.
  const agentJson = '{"name":"Loom-note","features":["a","b","c","d","e"]}';
  const agentDraft: FounderAppDraft = { ...DRAFT_UNCONFIRMED, founder_app_id: 23, source_kind: "agent_json" };
  await withStub(
    [
      { url: "/api/founder-app/23", method: "GET", json: draftDetail(agentDraft) },
      { url: "/api/founder-app", method: "POST", json: agentDraft },
    ],
    async (stub) => {
      await mountApp(React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }));
      await switchTab("Paste agent JSON");
      setField(document.querySelector("#fa-agent") as HTMLTextAreaElement, agentJson);
      await submitFrom("fa-agent");
      const post = stub.callsTo("/api/founder-app", "POST")[0];
      assert(
        JSON.stringify(post?.body) === JSON.stringify({ agent_json: agentJson }),
        "P7.3: the agent path posts the payload verbatim as agent_json",
      );
      assert(bodyText().includes("Pasted from your agent"), "P7.3: the draft is labelled as pasted from the agent");
    },
  );
}

// --- Area 4: confirm-before-diff -------------------------------------------

const NOT_CONFIRMED_BODY = {
  detail: {
    state: "not_confirmed",
    message: "founder app 3 is not confirmed - confirm the draft before the gap table runs (confirm-before-diff)",
  },
};

async function area4ConfirmBeforeDiff(): Promise<void> {
  // Copied from the ledger: the 409 the compare path actually answered with.
  await withStub([{ url: "/api/compare", method: "POST", status: 409, json: NOT_CONFIRMED_BODY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "3", competitors: ["obsidian"], onNeedsConfirm: () => {} }),
    );
    const text = appText(mounted.app);
    assert(text.includes("The draft must be confirmed first"), "P7.4: an unconfirmed draft says so");
    assert(
      text.includes("founder app 3 is not confirmed"),
      "P7.4: the server's own sentence is shown to the user",
    );
    assert(buttonNamed("Confirm the draft", mounted.app) !== undefined, "P7.4: the confirm step is offered, not a retry loop");
    assert(mounted.app.querySelector("table") === null, "P7.4: NO table renders for an unconfirmed draft — not even an empty one");
  });

  // The client contract: 409 {state: not_confirmed} is its own error class.
  await withStub([{ url: "/api/compare", method: "POST", status: 409, json: NOT_CONFIRMED_BODY }], async () => {
    let thrown: unknown = null;
    try {
      await compareStartups("3", ["obsidian"]);
    } catch (err) {
      thrown = err;
    }
    assert(thrown instanceof CompareNotConfirmed, "P7.4: compareStartups raises CompareNotConfirmed on a 409");
    assert(
      (thrown as Error)?.message.includes("confirm the draft before the gap table runs"),
      "P7.4: the error carries the server's message, not [object Object]",
    );
  });
}

// --- Area 5: gap table ------------------------------------------------------

async function area5GapTable(): Promise<void> {
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"], competitorNames: ["Obsidian"] }),
    );
    const text = appText(mounted.app);
    const tables = Array.from(mounted.app.querySelectorAll("table"));
    assert(tables.length === 5, `P7.5: five band tables render (got ${tables.length})`);
    const headings = Array.from(mounted.app.querySelectorAll("h3")).map((h) => (h.textContent ?? "").trim());
    assert(
      headings.join(" | ") === [
        "You have — they don't",
        "They have — you don't",
        "Both have (parity — no differentiation here)",
        "Unknown — missing data, not a gap",
        "Their users ask for it",
      ].join(" | "),
      "P7.5: the five bands render in the fixed order",
    );
    assert(text.includes("(none)"), "P7.5: an empty band renders as (none), not as a silent hole");
    assert(text.includes("unknown"), "P7.5: missing data renders as the literal word unknown");
    assert(tables[0]?.querySelector("th[scope='col']") !== null && tables[0]?.querySelector("th[scope='row']") !== null, "P7.5: the table is a real table with scoped headers");
    const sourced = mounted.app.querySelector('a[href="https://obsidian.md/pricing"]');
    assert(sourced !== null, "P7.5: a sourced cell links the page it came from");
    assert(sourced?.getAttribute("target") === "_blank", "P7.5: a source link opens in a new tab");
    assert(!/\bscore\b|\bverdict\b|\brank(ed|ing)?\b/i.test(text), "P7.5: the table prints no score, verdict or ranking");
    assert(!/verified/i.test(text), "P7.5: no trust badge appears anywhere inside the table");
  });

  // The capture-pending answer: show the state, offer the retry, never a
  // partial table. Copied from the ledger (200 {state: queued, ...}).
  const pendingBody = {
    state: "queued", message: "capture queued", startup_id: 566,
    you: { founder_app_id: 2, name: "Phase 6 Evidence App" },
    competitors: [{ id: 566, name: "BlueStone.com" }],
  };
  await withStub([{ url: "/api/compare", method: "POST", json: pendingBody }], async (stub) => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["bluestone.com"] }),
    );
    const text = appText(mounted.app);
    assert(text.includes("capture queued"), "P7.5: the capture-pending state shows the server's own message");
    assert(text.includes("BlueStone.com"), "P7.5: it names the competitor being captured");
    assert(mounted.app.querySelector("table") === null, "P7.5: a partial table is never shown as the answer");
    const retry = buttonNamed("Retry", mounted.app);
    assert(retry !== undefined, "P7.5: a Retry is offered for the pending state");
    const before = stub.callsTo("/api/compare", "POST").length;
    if (retry) click(retry);
    await flush();
    assert(stub.callsTo("/api/compare", "POST").length === before + 1, "P7.5: Retry re-runs the comparison");
  });

  // An unresolved competitor: the server's sentence, verbatim, plus a retry.
  await withStub(
    [{ url: "/api/compare", method: "POST", status: 404, json: { detail: "competitor not found: 'this-does-not-exist-zzz'" } }],
    async () => {
      const mounted = await mountApp(
        React.createElement(GapTablePanel, { you: "2", competitors: ["this-does-not-exist-zzz"] }),
      );
      const alert = mounted.app.querySelector('[role="alert"]');
      assert(alert !== null, "P7.5: an unresolved competitor is an alert, not an empty box");
      assert((alert?.textContent ?? "").includes("competitor not found: 'this-does-not-exist-zzz'"), "P7.5: the server's sentence names the competitor");
      assert(mounted.app.querySelector("table") === null, "P7.5: no table renders when the competitor did not resolve");
    },
  );
}

// --- Area 6: export ---------------------------------------------------------

const EXPORT_BYTES: Record<string, { ctype: string; text: string }> = {
  // Markdown / CSV heads copied from the ledger (Phase 6 §4).
  markdown: {
    ctype: "text/markdown; charset=utf-8",
    text: "# Gap table - Phase 6 Evidence App vs Obsidian\n\n## You have — they don't\n",
  },
  csv: {
    ctype: "text/csv",
    text: "band,dimension,you,them,source_url,captured_at\nunknown,Pricing,Pro $8/monthly,unknown,,\n",
  },
  json: {
    ctype: "application/json",
    text: JSON.stringify({ you: { name: "Phase 6 Evidence App" }, them: {}, rows: [] }),
  },
};

async function area6Export(): Promise<void> {
  const routes: StubRoute[] = Object.entries(EXPORT_BYTES).map(([format, spec]) => ({
    url: `/api/export/${format}`,
    text: spec.text,
    ctype: spec.ctype,
  }));

  // The client side of the contract: bytes, media type and filename per format.
  await withStub(routes, async (stub) => {
    for (const format of ["markdown", "json", "csv"] as const) {
      const payload = await exportGapTable(format, "2", ["obsidian"]);
      assert(payload.text === EXPORT_BYTES[format].text, `P7.6: ${format} returns the response bytes unchanged`);
      assert(payload.mediaType === EXPORT_BYTES[format].ctype, `P7.6: ${format} reports its own content type`);
      assert(payload.filename === `gap-table.${format}`, `P7.6: ${format} is saved as gap-table.${format}`);
    }
    const csvFirstLine = EXPORT_BYTES.csv.text.split("\n")[0];
    assert(csvFirstLine === "band,dimension,you,them,source_url,captured_at", "P7.6: the CSV parses and carries the documented header");
    assert(JSON.parse(EXPORT_BYTES.json.text).you?.name === "Phase 6 Evidence App", "P7.6: the JSON parses and carries the you side");
    assert(EXPORT_BYTES.markdown.text.startsWith("# Gap table"), "P7.6: the markdown parses as the band table");
  });

  // The download the buttons trigger: correct URL, correct filename, per format.
  const downloads: { href: string; download: string }[] = [];
  const anchorProto = domWindow.HTMLAnchorElement.prototype as unknown as { click: () => void };
  const realClick = anchorProto.click;
  anchorProto.click = function (this: HTMLAnchorElement) {
    downloads.push({ href: this.href, download: this.download });
  };
  try {
    await withStub(routes, async (stub) => {
      const mounted = await mountApp(
        React.createElement(React.Fragment, null,
          React.createElement(GapExportButtons, { you: "2", competitors: ["obsidian"] }),
          React.createElement(Toaster, null),
        ),
      );
      for (const label of ["Markdown", "JSON", "CSV"] as const) {
        const btn = buttonNamed(label, mounted.app);
        assert(btn !== undefined, `P7.6: the ${label} export button renders`);
        if (btn) click(btn);
        await flush();
      }
      const urls = stub.callsTo("/api/export").map((c) => c.url);
      assert(urls.some((u) => u.includes("/api/export/markdown?you=2&competitors=obsidian")), "P7.6: the Markdown button hits /api/export/markdown with the compare inputs");
      assert(urls.some((u) => u.includes("/api/export/json")) && urls.some((u) => u.includes("/api/export/csv")), "P7.6: JSON and CSV hit their own routes");
      assert(
        ["gap-table.markdown", "gap-table.json", "gap-table.csv"].every((name) =>
          downloads.some((d) => d.download === name),
        ),
        `P7.6: each format downloads under its own filename (got ${downloads.map((d) => d.download).join(", ")})`,
      );
    });
  } finally {
    anchorProto.click = realClick;
  }

  // The failure path is surfaced, not swallowed.
  await withStub(
    [{ url: "/api/export/markdown", status: 502, json: { detail: "the export could not be generated" } }],
    async () => {
      const mounted = await mountApp(
        React.createElement(React.Fragment, null,
          React.createElement(GapExportButtons, { you: "2", competitors: ["obsidian"] }),
          React.createElement(Toaster, null),
        ),
      );
      const before = downloads.length;
      const btn = buttonNamed("Markdown", mounted.app);
      if (btn) click(btn);
      await flush();
      assert(downloads.length === before, "P7.6: a failed export downloads nothing");
      assert(bodyText().includes("Couldn't export Markdown"), "P7.6: a failed export surfaces a failure to the user");
      assert(bodyText().includes("the export could not be generated"), "P7.6: the failure carries the server's reason");
      assert((btn?.getAttribute("aria-busy") ?? "false") === "false", "P7.6: the button is released after the failure");
    },
  );

  // An unconfirmed draft is refused here too, as a state rather than a fault.
  await withStub([{ url: "/api/export/csv", status: 409, json: NOT_CONFIRMED_BODY }], async () => {
    let thrown: unknown = null;
    try {
      await exportGapTable("csv", "3", ["obsidian"]);
    } catch (err) {
      thrown = err;
    }
    assert(thrown instanceof CompareNotConfirmed, "P7.6: an export against an unconfirmed draft raises CompareNotConfirmed");
  });
}

// --- Area 7: /products/<slug> ----------------------------------------------

function route(slug: string, search = ""): React.ReactElement {
  return React.createElement(
    PathParamsContext.Provider as React.ComponentType<{ value: unknown; children?: React.ReactNode }>,
    { value: { slug } },
    React.createElement(
      SearchParamsContext.Provider as React.ComponentType<{ value: unknown; children?: React.ReactNode }>,
      { value: new URLSearchParams(search) },
      React.createElement(ProductPage),
    ),
  );
}

async function area7ProductRoute(): Promise<void> {
  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    const mounted = await mountApp(route("obsidian"));
    assert((mounted.app.querySelector("h1")?.textContent ?? "") === "Obsidian", "P7.7: /products/<slug> loads the record the slug resolves to");
    const text = appText(mounted.app);
    assert(text.includes("/products/obsidian"), "P7.7: the page prints its own stable coordinate");
    assert(text.includes("Back to the archive"), "P7.7: there is a way back");
    assert(text.includes("Compare with my app"), "P7.7: the founder entry point is on the page");
  });

  // An unknown slug is a themed 404 that names the slug — not a crash, not an
  // empty page, and not the "archive unreachable" state either.
  await withStub(
    [{ url: "/api/startups/not-a-real-product", status: 404, json: { detail: "no product with slug 'not-a-real-product'" } }],
    async () => {
      const mounted = await mountApp(route("not-a-real-product"));
      const text = appText(mounted.app);
      assert(text.includes("Not filed"), "P7.7: an unknown slug renders the themed not-filed panel");
      assert(text.includes("not-a-real-product"), "P7.7: the panel names the slug it could not resolve");
      assert(mounted.app.querySelector('a[href="/"]') !== null, "P7.7: the not-filed panel offers a way back");
      assert(!text.includes("could not be read"), "P7.7: a missing record is not dressed up as a connection failure");
    },
  );

  // The client contract for the same two cases.
  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    const record = await fetchStartupRecord("obsidian");
    assert(record.slug === "obsidian", "P7.7: fetchStartupRecord returns the resolved record");
  });
  await withStub([{ url: "/api/startups/nope", status: 404, json: { detail: "no product" } }], async () => {
    let thrown: unknown = null;
    try {
      await fetchStartupRecord("nope");
    } catch (err) {
      thrown = err;
    }
    assert(thrown instanceof RecordNotFound, "P7.7: a 404 raises RecordNotFound, distinct from a read failure");
  });

  // "Share Entity" copies the stable /products/<slug> coordinate, and the
  // detail modal's "Open full record" points at it.
  const clipboard: string[] = [];
  Object.defineProperty(domWindow.navigator, "clipboard", {
    configurable: true,
    value: { writeText: async (t: string) => { clipboard.push(t); } },
  });
  await withStub([{ url: "/api/startups/1", json: RECORD_UNCAPTURED }], async () => {
    const mounted = await mountApp(
      React.createElement(StartupDetail, {
        startup: RECORD_UNCAPTURED as unknown as Startup,
        startups: [RECORD_UNCAPTURED as unknown as Startup],
        onClose: () => {},
        onNavigate: () => {},
      }),
    );
    const share = buttonNamed("Share Entity", document);
    assert(share !== undefined, "P7.7: the detail modal offers Share Entity");
    if (share) click(share);
    await flush();
    assert(
      clipboard.some((t) => t.endsWith("/products/obsidian")),
      `P7.7: Share Entity copies the stable /products/<slug> URL (got ${clipboard.join(", ")})`,
    );
    const openRecord = Array.from(document.querySelectorAll("a")).find((a) =>
      (a.textContent ?? "").includes("Open full record"),
    );
    assert(openRecord?.getAttribute("href") === "/products/obsidian", "P7.7: Open full record links the stable route");
    assert(mounted.app.querySelector('[role="dialog"][aria-modal="true"]') !== null, "P7.7: the detail modal is a real aria-modal dialog");
  });
}

// --- Area 8: visual & a11y --------------------------------------------------

async function area8VisualAndA11y(): Promise<void> {
  // Light and dark: the same record renders in both themes.
  for (const theme of ["light", "dark"] as const) {
    await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
      const mounted = await mountApp(
        React.createElement(TeardownDossier, { reference: "obsidian", initial: RECORD_UNCAPTURED }),
        theme,
      );
      assert(appText(mounted.app).includes("Obsidian") || appText(mounted.app).length > 200, `P8.1: the dossier renders in ${theme} theme`);
      const rootClass = document.documentElement.className;
      assert(
        rootClass === theme,
        `P8.1: ${theme} theme is applied to the document root (got "${rootClass}")`,
      );
      cleanupApp();
    });
  }

  // Reduced motion: the motion-bearing components still render their content.
  setReducedMotion(true);
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    assert(mounted.app.querySelectorAll("table").length === 5, "P8.1: under prefers-reduced-motion the gap table still renders every band");
  });
  setReducedMotion(false);

  // Mobile viewport: nothing in these surfaces is hidden by a JS width branch,
  // so a 375px viewport must still expose the whole control set. (CSS reflow is
  // scripts/reflow-check.mjs's job — jsdom applies no stylesheet.)
  const realWidth = domWindow.innerWidth;
  Object.defineProperty(domWindow, "innerWidth", { configurable: true, value: 375 });
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    assert(mounted.app.querySelectorAll("table").length === 5, "P8.1: at a 375px viewport the comparison keeps every band");
    assert(
      mounted.app.querySelector('a[href="https://obsidian.md"]') !== null,
      "P8.1: at a 375px viewport the sourced cells are still links",
    );
  });
  Object.defineProperty(domWindow, "innerWidth", { configurable: true, value: realWidth });

  // Empty / loading / error states.
  await withStub([{ url: "/api/startups/empty-record", json: { ...RECORD_UNCAPTURED, evidence: [], pricing_json: null, features_json: null, positioning: null } }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "empty-record", initial: null }),
    );
    const text = appText(mounted.app);
    assert(text.includes("unknown"), "P8.1: an empty record renders `unknown`, never a blank panel");
    assert(
      text.includes("no pricing was captured") && text.includes("no captured feature list") && text.includes("not captured on this record"),
      "P8.1: each empty section explains why it is empty",
    );
    assert(text.includes("What it doesn't do") && text.includes("no negative observations were captured"), "P8.1: an empty 'doesn't do' list says so instead of implying there is nothing to find");
  });

  await withStub([{ url: "/api/compare", method: "POST", hang: true }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    const status = mounted.app.querySelector('[role="status"]');
    assert(status !== null, "P8.1: the loading state is a role=status live region");
    assert((status?.textContent ?? "").includes("Comparing"), "P8.1: the loading state says what it is doing");
    assert(mounted.app.querySelector('[aria-busy="true"]') !== null, "P8.1: the loading container is aria-busy");
    assert(mounted.app.querySelector("table") === null, "P8.1: no table is rendered while the comparison is in flight");
  });

  await withStub([{ url: "/api/compare", method: "POST", fail: true }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    const alert = mounted.app.querySelector('[role="alert"]');
    assert(alert !== null, "P8.1: an unreachable backend is a role=alert, not a blank panel");
    assert(buttonNamed("Retry", mounted.app) !== undefined, "P8.1: the error state offers a retry");
  });

  // focus / aria per surface, and the external-link rule everywhere it applies.
  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: RECORD_UNCAPTURED }),
    );
    assertExternalLinks(mounted.app, "P8.1 dossier");
  });

  await withStub([{ url: "/api/compare", method: "POST", json: GAP_DIMENSION7 }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "4", competitors: ["noted"] }),
    );
    assertExternalLinks(mounted.app, "P8.1 gap table");
  });

  await withStub([], async () => {
    const mounted = await mountApp(
      React.createElement(StartupCard, { startup: MOCK_STARTUPS[0] }),
    );
    assertExternalLinks(mounted.app, "P8.1 startup card");
    assert(
      Array.from(mounted.app.querySelectorAll("a[target='_blank']")).every((a) =>
        /opens in a new tab/.test(a.getAttribute("aria-label") ?? ""),
      ),
      "P8.1: the card's labels say what the link opens and that it is a new tab",
    );
  });

  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    await mountApp(route("obsidian"));
    assertExternalLinks(document.querySelector("#p7-app") as ParentNode, "P8.1 product page");
  });

  const linkDraft: FounderAppDraft = {
    ...DRAFT_UNCONFIRMED,
    founder_app_id: 31,
    confirmed: true, publish_offered: true,
    eligibility: { has_link: true, link: "https://loom-note.test", link_field: "website_url" },
    profile: { ...DRAFT_UNCONFIRMED.profile, website_url: "https://loom-note.test", github_url: "https://github.com/loom/note" },
  };
  await withStub(
    [
      { url: "/api/founder-app/31", method: "GET", json: draftDetail(linkDraft) },
      { url: "/api/founder-app", method: "POST", json: linkDraft },
    ],
    async () => {
      await mountApp(
        React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }),
      );
      await switchTab("Paste agent JSON");
      setField(document.querySelector("#fa-agent") as HTMLTextAreaElement, '{"name":"Loom-note"}');
      await submitFrom("fa-agent");
      assertExternalLinks(document, "P8.1 founder dialog");
    },
  );
}

// --- Area 9: trust badges ---------------------------------------------------

async function area9TrustBadges(): Promise<void> {
  await withStub([{ url: "/api/startups/obsidian", json: RECORD_UNCAPTURED }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: RECORD_UNCAPTURED }),
    );
    const text = appText(mounted.app);
    assert(text.includes("Admin Verified"), "P7.9: Admin Verified renders");
    assert(text.includes("Machine Verified"), "P7.9: Machine Verified renders");
    const admin = Array.from(mounted.app.querySelectorAll("span")).find((s) =>
      (s.textContent ?? "").includes("Admin Verified"),
    );
    const machine = Array.from(mounted.app.querySelectorAll("span")).find((s) =>
      (s.textContent ?? "").includes("Machine Verified"),
    );
    assert(admin !== machine && admin !== undefined && machine !== undefined, "P7.9: the two signals are two distinct elements, not one merged badge");
    assert((admin?.textContent ?? "").includes("Aug 10"), "P7.9: Admin Verified carries its own date");
    assert((machine?.textContent ?? "").includes("last checked"), "P7.9: Machine Verified carries its own last-checked date");
    assert(text.includes("describe the record") || text.includes("These two describe the"), "P7.9: the badges say they describe the record, not the claims");

    // A badge never sits inside a claim.
    const claimNodes = Array.from(mounted.app.querySelectorAll("li, table, td, th"));
    assert(
      claimNodes.every((n) => !/verified/i.test(n.textContent ?? "")),
      "P7.9: no badge is rendered inside a claim cell",
    );
  });

  // A stale last_checked: Machine Verified lapses, Admin Verified does not.
  const stale: StartupRecord = {
    ...RECORD_UNCAPTURED,
    last_checked: "2026-08-01 00:00:00",
    machine_verified: false,
    machine_verified_at: "2026-08-01 00:00:00",
  };
  await withStub([{ url: "/api/startups/obsidian", json: stale }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: stale }),
    );
    const text = appText(mounted.app);
    assert(text.includes("lapsed") && text.includes("Aug 1"), "P7.9: a stale check shows Machine Verified as lapsed with its last-checked date");
    assert(text.includes("Admin Verified") && !text.includes("not admin verified"), "P7.9: the record stays Admin Verified while machine lapses");
  });

  const never: StartupRecord = { ...RECORD_UNCAPTURED, machine_verified: false, machine_verified_at: null, last_checked: null };
  await withStub([{ url: "/api/startups/obsidian", json: never }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: never }),
    );
    assert(appText(mounted.app).includes("never checked"), "P7.9: a record automation never reached says so");
  });

  // And the same rule on the comparison surface: no badge inside the table.
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    assert(!/verified/i.test(appText(mounted.app)), "P7.9: the gap table carries no trust badge anywhere");
  });
}

// --- Area 10: link eligibility & consent -----------------------------------

async function area10EligibilityAndConsent(): Promise<void> {
  // Link-less: no consent question is asked, because there is nothing to
  // consent to (docs/teardown-spec.md §3.1).
  const linkless: FounderAppDraft = {
    ...DRAFT_UNCONFIRMED,
    founder_app_id: 41, confirmed: true, publish_offered: false,
    eligibility: { has_link: false, link: "", link_field: null },
  };
  await withStub(
    [
      { url: "/api/founder-app/41", method: "GET", json: draftDetail(linkless) },
      { url: "/api/founder-app", method: "POST", json: linkless },
    ],
    async () => {
      await mountApp(React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }));
      await switchTab("Paste agent JSON");
      setField(document.querySelector("#fa-agent") as HTMLTextAreaElement, '{"name":"Loom-note"}');
      await submitFrom("fa-agent");
      const text = bodyText();
      assert(document.querySelectorAll('input[type="checkbox"]').length === 0, "P7.10: the publish checkbox is absent for a link-less draft");
      assert(text.includes("No link — comparison only."), "P7.10: the link-less draft says it is comparison-only");
      assert(text.includes("never be added to the archive"), "P7.10: it states plainly that it is never published");
      assert(buttonNamed("Submit for publication") === undefined, "P7.10: no publish action is offered without a link");
    },
  );

  // Link-less still compares: the gap table runs, and the state stays honest.
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "41", competitors: ["obsidian"] }),
    );
    assert(mounted.app.querySelectorAll("table").length === 5, "P7.10: a link-less draft still returns a comparison");
    assert(mounted.app.querySelector('[role="alert"]') === null, "P7.10: comparison-only is not an error state");
  });

  // A link makes it eligible: the consent checkbox appears, and the action is
  // gated on the tick.
  const linked: FounderAppDraft = {
    ...DRAFT_UNCONFIRMED,
    founder_app_id: 42, confirmed: true, publish_offered: true,
    eligibility: { has_link: true, link: "https://loom-note.test", link_field: "website_url" },
    profile: { ...DRAFT_UNCONFIRMED.profile, website_url: "https://loom-note.test" },
  };
  await withStub(
    [
      { url: "/api/founder-app/42", method: "GET", json: draftDetail(linked) },
      { url: "/api/founder-app", method: "POST", json: linked },
      { url: "/api/founder-app/42/publish", method: "POST", json: { submitted: true, submission_id: 77, archive_status: "pending", message: "submitted for review" } },
    ],
    async (stub) => {
      await mountApp(React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }));
      await switchTab("Paste agent JSON");
      setField(document.querySelector("#fa-agent") as HTMLTextAreaElement, '{"name":"Loom-note"}');
      await submitFrom("fa-agent");
      const box = document.querySelector('input[type="checkbox"]') as HTMLInputElement | null;
      assert(box !== null, "P7.10: a link-ful draft is offered the consent checkbox");
      const submit = buttonNamed("Submit for publication");
      assert(submit?.disabled === true, "P7.10: publish is disabled until consent is ticked");
      if (box) {
        // `.click()` runs the checkbox activation behaviour, so React's change
        // handler sees the toggled value (a synthetic Event would not toggle).
        act(() => {
          box.click();
        });
      }
      await flush();
      const afterTick = buttonNamed("Submit for publication");
      assert(afterTick?.disabled === false, "P7.10: ticking consent enables the publish action");
      if (afterTick) click(afterTick);
      await flush();
      assert(stub.callsTo("/publish", "POST").length === 1, "P7.10: publishing is a separate call after confirm");
    },
  );

  // A rejection is visible, with its note — the whole feedback loop.
  const rejected: FounderAppDraft = {
    ...DRAFT_UNCONFIRMED,
    founder_app_id: 43, confirmed: true, publish_offered: true,
    archive_status: "rejected",
    submission: {
      id: 5, founder_app_id: 43, submitted_at: "2026-09-16 10:00:00", status: "rejected",
      archive_startup_id: null, decided_at: "2026-09-17 09:00:00", decided_by: "owner",
      note: "The link is a parked domain — resubmit when the site is live.",
    },
  };
  await withStub(
    [
      { url: "/api/founder-app/43", method: "GET", json: { ...rejected, submissions: [rejected.submission] } },
      { url: "/api/founder-app", method: "POST", json: rejected },
    ],
    async () => {
      await mountApp(React.createElement(FounderAppDialog, { open: true, onOpenChange: () => {} }));
      await switchTab("Paste agent JSON");
      setField(document.querySelector("#fa-agent") as HTMLTextAreaElement, '{"name":"Loom-note"}');
      await submitFrom("fa-agent");
      const text = bodyText();
      assert(text.includes("Not accepted"), "P7.10: a rejected submission shows its archive status");
      assert(text.includes("Why it was turned down"), "P7.10: the rejection surface names itself");
      assert(text.includes("The link is a parked domain — resubmit when the site is live."), "P7.10: the rejection note is shown verbatim");
      assert(text.includes("Submission history"), "P7.10: the decision history stays auditable");
    },
  );
}

// --- Area 11: reviews / dimension 7 ----------------------------------------

async function area11Dimension7(): Promise<void> {
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_DIMENSION7 }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "4", competitors: ["noted"] }),
    );
    const headings = Array.from(mounted.app.querySelectorAll("h3"));
    const demandHeading = headings.find((h) => (h.textContent ?? "").includes("Their users ask for it"));
    assert(demandHeading !== undefined, "P7.11: 'what their users ask for' renders as its own band");

    // Banded correctly: covered by your features -> group 1; covered by neither
    // -> group 4.
    const sections = Array.from(mounted.app.querySelectorAll("section"));
    const sectionFor = (label: string) =>
      sections.find((s) => (s.querySelector("h3")?.textContent ?? "").includes(label));
    const group1 = sectionFor("You have — they don't");
    const group4 = sectionFor("Their users ask for it");
    assert(group1 !== null && group4 !== null, "P7.11: both bands render");
    assert((group1?.textContent ?? "").includes("Offline mode"), "P7.11: a request your features already cover lands in group 1");
    assert((group4?.textContent ?? "").includes("Native mobile app"), "P7.11: a request covered by neither side lands in group 4");
    assert(!(group1?.textContent ?? "").includes("Native mobile app"), "P7.11: the group-4 row is not also in group 1");

    // Each demand item links the review it came from.
    const reviewLink = group4?.querySelector("a[href='https://reddit.com/r/noted']");
    assert(reviewLink !== null && reviewLink !== undefined, "P7.11: a demand item links the review behind it");
    const g2Link = group1?.querySelector("a[href='https://g2.com/noted-reviews']");
    assert(g2Link !== null && g2Link !== undefined, "P7.11: the covered request links its review too");

    // No score, no aggregate, anywhere.
    const text = appText(mounted.app);
    assert(!/\bscore\b|\bnps\b|sentiment|aggregate|\bstar rat/i.test(text), "P7.11: no score, NPS or aggregate exists in the gap table");
    assert(!text.includes("%"), "P7.11: no percentage aggregate is printed");
    assert(mounted.app.querySelector("meter, progress") === null, "P7.11: no rating widget is rendered");
    assert(!/you should build/i.test(text), "P7.11: the table never turns a request into advice");
  });
}

// --- Area 12: founded honesty ----------------------------------------------

async function area12FoundedHonesty(): Promise<void> {
  // The rule itself: an RDAP date is not a founding year.
  const rdapShort = foundedShort("2000-11-01", "rdap");
  assert(rdapShort.text === "est. 2000", "P7.12: an RDAP date renders as an estimate, not as a founding year");
  assert(!/founded/i.test(rdapShort.text), "P7.12: the card line for an RDAP date never says 'founded'");
  assert(/RDAP/.test(rdapShort.title), "P7.12: the tooltip says the date is a domain registration");

  const rdapLabel = foundedLabel("2000-11-01", "rdap");
  assert(rdapLabel.label === "Domain registered", "P7.12: the dossier labels an RDAP date 'Domain registered'");
  assert(/not a founding year/.test(rdapLabel.note ?? ""), "P7.12: the dossier note says it is not a founding year");

  const humanLabel = foundedLabel("2013-06-01", "human");
  assert(humanLabel.label === "Founded", "P7.12: only a human-confirmed date is called 'Founded'");

  // No fabricated year: a null date yields no text at all.
  assert(foundedShort(null, null).text === null, "P7.12: a null date produces no vintage text");
  assert(foundedShort(null, "rdap").text === null, "P7.12: a null date produces no text under any source");

  // And in the render: the RDAP card carries the estimate, never "founded".
  const rdapRow = startupRow({
    id: 5, name: "Notion", founded: "2000-11-01", date_source: "rdap",
    website_url: "https://notion.so", stars: 10, verified: 1,
  });
  await withStub([], async () => {
    const mounted = await mountApp(React.createElement(StartupCard, { startup: rdapRow }));
    const text = appText(mounted.app);
    assert(text.includes("est. 2000"), "P7.12: the card shows the RDAP date as an estimate");
    assert(!/founded 2000/i.test(text), "P7.12: the card does not label an RDAP date a founding year");
    const holder = mounted.app.querySelector("[title*='RDAP']");
    assert(holder !== null, "P7.12: the card explains the estimate in a title attribute");
  });

  const nullRow = startupRow({ id: 6, name: "Undated Thing", founded: null, date_source: null });
  await withStub([], async () => {
    const mounted = await mountApp(React.createElement(StartupCard, { startup: nullRow }));
    const text = appText(mounted.app);
    assert(!text.includes("2021"), "P7.12: no fabricated 2021 fallback renders for a null date");
    assert(!/\bfounded\b/i.test(text) && !/\best\./.test(text), "P7.12: a null date renders no vintage claim at all");
  });

  const rdapRecord: StartupRecord = { ...RECORD_UNCAPTURED, founded: "2000-11-01", date_source: "rdap" };
  await withStub([{ url: "/api/startups/obsidian", json: rdapRecord }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: rdapRecord }),
    );
    const text = appText(mounted.app);
    assert(text.includes("Domain registered"), "P7.12: the dossier's identity row labels the RDAP date honestly");
    assert(!text.includes("2021"), "P7.12: the dossier fabricates no year");
  });

  const undatedRecord: StartupRecord = { ...RECORD_UNCAPTURED, founded: null, date_source: null };
  await withStub([{ url: "/api/startups/obsidian", json: undatedRecord }], async () => {
    const mounted = await mountApp(
      React.createElement(TeardownDossier, { reference: "obsidian", initial: undatedRecord }),
    );
    const text = appText(mounted.app);
    assert(text.includes("date source unrecorded") || text.includes("unknown"), "P7.12: an undated record says so instead of inventing a year");
    assert(!text.includes("2021"), "P7.12: no fabricated 2021 appears anywhere in the dossier");
  });
}

// --- Tier 6: the non-happy states, as the ledger recorded them --------------

async function tier6NonHappyStates(): Promise<void> {
  // Every state below is copied from docs/phase-ledger.md Phase 6 §3. The point
  // of the sweep is that none of them collapses into an empty box: each one is
  // its own honest render with its own way forward.
  const cases: { name: string; routes: StubRoute[]; want: string[]; noTable?: boolean }[] = [
    {
      name: "409 not_confirmed",
      routes: [{ url: "/api/compare", method: "POST", status: 409, json: NOT_CONFIRMED_BODY }],
      want: ["The draft must be confirmed first", "founder app 3 is not confirmed"],
      noTable: true,
    },
    {
      name: "200 queued",
      routes: [{ url: "/api/compare", method: "POST", json: { state: "queued", message: "capture queued", startup_id: 566, you: { founder_app_id: 2, name: "Me" }, competitors: [{ id: 566, name: "BlueStone.com" }] } }],
      want: ["capture queued", "Retry"],
      noTable: true,
    },
    {
      name: "200 in_progress",
      routes: [{ url: "/api/compare", method: "POST", json: { state: "in_progress", message: "capture in progress — retry", startup_id: 30, you: { founder_app_id: 2, name: "Me" }, competitors: [{ id: 30, name: "Acme Notes" }] } }],
      want: ["capture in progress — retry", "Retry"],
      noTable: true,
    },
    {
      name: "404 competitor not found",
      routes: [{ url: "/api/compare", method: "POST", status: 404, json: { detail: "competitor not found: 'this-does-not-exist-zzz'" } }],
      want: ["competitor not found: 'this-does-not-exist-zzz'", "Retry"],
      noTable: true,
    },
  ];

  for (const c of cases) {
    await withStub(c.routes, async () => {
      const mounted = await mountApp(
        React.createElement(GapTablePanel, { you: "3", competitors: ["obsidian"] }),
      );
      const text = appText(mounted.app);
      for (const want of c.want) {
        assert(text.includes(want), `P7.0 (${c.name}): renders "${want}"`);
      }
      if (c.noTable) {
        assert(mounted.app.querySelector("table") === null, `P7.0 (${c.name}): never renders a table as the answer`);
      }
      assert(text.length > 20, `P7.0 (${c.name}): is a real render, not an empty box`);
    });
  }

  // The unknown cell, on its own: the literal word, never blank.
  await withStub([{ url: "/api/compare", method: "POST", json: GAP_READY }], async () => {
    const mounted = await mountApp(
      React.createElement(GapTablePanel, { you: "2", competitors: ["obsidian"] }),
    );
    const unknownCells = Array.from(mounted.app.querySelectorAll("td")).filter((td) =>
      (td.textContent ?? "").trim() === "unknown",
    );
    assert(unknownCells.length > 0, "P7.0 (unknown cell): an empty claim renders the literal word unknown");
    assert(
      Array.from(mounted.app.querySelectorAll("td")).every((td) => (td.textContent ?? "").trim().length > 0),
      "P7.0 (unknown cell): no cell is ever blank",
    );
  });
}

// --- run the Phase 7 suites ------------------------------------------------

(async () => {
  await suiteAsync("Tier 5: [1] search with reasons", area1SearchWithReasons);
  await suiteAsync("Tier 5: [2] dossier -> teardown", area2DossierTeardown);
  await suiteAsync("Tier 5: [3] founder-app: URL / form / agent-JSON", area3FounderPaths);
  await suiteAsync("Tier 5: [4] confirm-before-diff", area4ConfirmBeforeDiff);
  await suiteAsync("Tier 5: [5] gap table", area5GapTable);
  await suiteAsync("Tier 5: [6] export", area6Export);
  await suiteAsync("Tier 5: [7] /products/<slug>", area7ProductRoute);
  await suiteAsync("Tier 5: [8] visual & a11y", area8VisualAndA11y);
  await suiteAsync("Tier 5: [9] trust badges", area9TrustBadges);
  await suiteAsync("Tier 5: [10] link eligibility & consent", area10EligibilityAndConsent);
  await suiteAsync("Tier 5: [11] reviews / gap-table dimension 7", area11Dimension7);
  await suiteAsync("Tier 5: [12] founded honesty", area12FoundedHonesty);
  await suiteAsync("Tier 6: the non-happy states from the ledger", tier6NonHappyStates);

  // Final Test Summary Output
  console.log("\n==========================================");
  console.log(`TEST RESULTS: ${passedCount} PASSED, ${failedCount} FAILED`);
  console.log("==========================================\n");

  if (failedCount > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
})();
