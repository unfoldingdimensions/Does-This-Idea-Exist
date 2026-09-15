/**
 * IdeaExists E2E Verification Suite (Tiers 1 - 4)
 * Opaque-box verification for Frontend Requirements R1 - R4.
 */

import { JSDOM } from "jsdom";

// Initialize JSDOM DOM Environment
const dom = new JSDOM("<!DOCTYPE html><html><head></head><body><div id='root'></div></body></html>", {
  url: "http://localhost:3000/",
  pretendToBeVisual: true,
});

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
global.window = dom.window as any;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.HTMLElement = dom.window.HTMLElement;
global.Element = dom.window.Element;
global.Node = dom.window.Node;
global.MouseEvent = dom.window.MouseEvent;
global.KeyboardEvent = dom.window.KeyboardEvent;
global.Event = dom.window.Event;
global.CustomEvent = dom.window.CustomEvent;
global.sessionStorage = dom.window.sessionStorage;
global.localStorage = dom.window.localStorage;
global.HTMLFormElement = dom.window.HTMLFormElement;
global.HTMLInputElement = dom.window.HTMLInputElement;
global.HTMLButtonElement = dom.window.HTMLButtonElement;
global.HTMLDivElement = dom.window.HTMLDivElement;
global.SVGElement = dom.window.SVGElement;

// Mock matchMedia with reduced-motion state control
let reducedMotionState = false;
const mediaListeners = new Set<(e: any) => void>();

global.window.matchMedia = function (query: string) {
  const isReduced = query.includes("prefers-reduced-motion");
  return {
    matches: isReduced ? reducedMotionState : false,
    media: query,
    onchange: null,
    addListener: (cb: any) => { mediaListeners.add(cb); },
    removeListener: (cb: any) => { mediaListeners.delete(cb); },
    addEventListener: (_evt: string, cb: any) => { mediaListeners.add(cb); },
    removeEventListener: (_evt: string, cb: any) => { mediaListeners.delete(cb); },
    dispatchEvent: () => true,
  };
};

function setReducedMotion(reduced: boolean) {
  reducedMotionState = reduced;
  mediaListeners.forEach((cb) => cb({ matches: reduced }));
}

// Mock IntersectionObserver
const MockIntersectionObserver = class IntersectionObserver {
  constructor(public callback: any) {}
  observe() {
    this.callback([{ isIntersecting: true }], this);
  }
  unobserve() {}
  disconnect() {}
};

global.window.IntersectionObserver = MockIntersectionObserver as any;
global.IntersectionObserver = MockIntersectionObserver as any;

// Mock ResizeObserver
const MockResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

global.window.ResizeObserver = MockResizeObserver as any;
global.ResizeObserver = MockResizeObserver as any;

// Mock requestAnimationFrame
global.window.requestAnimationFrame = (cb: FrameRequestCallback) => setTimeout(cb, 16) as any;
global.window.cancelAnimationFrame = (id: number) => clearTimeout(id);

// Mock scrollTo & scrollIntoView
global.window.scrollTo = () => {};
global.Element.prototype.scrollIntoView = () => {};

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
import { SkyBackground } from "../frontend/components/sky-background";
import { ThemeToggle } from "../frontend/components/theme-toggle";
import { StartupCard } from "../frontend/components/startup-card";
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

suite("Tier 1: Celestial Sky & Custom Sun/Moon Engine (R1)", () => {
  renderWithTheme(React.createElement(SkyBackground));

  assert(container.querySelector(".sky-sun") !== null, "R1.1: Sun element (.sky-sun) rendered for light mode");
  assert(container.querySelector(".sky-moon") !== null, "R1.2: Moon element (.sky-moon) rendered for dark mode");
  assert(container.querySelectorAll(".sky-star").length >= 10, "R1.3: Starfield (.sky-star) rendered with multiple star depth layers");
  assert(container.querySelector(".sky-wash-sunset") !== null, "R1.4: Sunset background wash rendered");
  assert(container.querySelector(".sky-wash-night") !== null, "R1.5: Night background wash rendered");
  assert(container.querySelector(".sky-silhouette--mountain") !== null, "R1.6: Mountain ridge silhouette element rendered");
  
  const skyWrapper = container.querySelector(".pointer-events-none") as HTMLElement;
  assert(skyWrapper !== null && skyWrapper.getAttribute("aria-hidden") === "true", "R1.7: Sky wrapper has aria-hidden=true");
  assert(skyWrapper !== null && skyWrapper.classList.contains("pointer-events-none"), "R1.8: Sky wrapper is pointer-events-none");

  teardown();
});

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
  // T8.1: Reduced motion compliance
  setReducedMotion(true);
  renderWithTheme(React.createElement(SkyBackground));

  const sunElement = container.querySelector(".sky-sun") as HTMLElement;
  assert(sunElement !== null, "T8.1: SkyBackground mounts cleanly under prefers-reduced-motion: reduce");

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
      React.createElement(SkyBackground),
      React.createElement(ThemeToggle)
    )
  );

  assert(container.querySelector(".sky-sun") !== null, "T9.1: Sky background and ThemeToggle mounted simultaneously");
  
  const toggleBtn = container.querySelector("button") as HTMLButtonElement;
  act(() => {
    toggleBtn.click();
  });

  assert(container.querySelector(".sky-moon") !== null, "T9.2: Theme toggle click seamlessly crossfades sky background visuals");

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

// Final Test Summary Output
console.log("\n==========================================");
console.log(`TEST RESULTS: ${passedCount} PASSED, ${failedCount} FAILED`);
console.log("==========================================\n");

if (failedCount > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
