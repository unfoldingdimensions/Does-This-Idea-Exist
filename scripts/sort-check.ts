/**
 * Regression check for sortStartups (frontend/lib/search.ts).
 *
 * The bug this pins: DEAD_ORDER used to run as a separate pre-sort pass, which
 * every switch case then discarded by re-sorting the whole array. Dead entries
 * interleaved with live ones under name/newest/founded. The fixture is built so
 * the dead entry wins every ordering on its own merits (newest, most stars,
 * first alphabetically, most recently founded) — so if dead-last ever stops
 * leading the comparator, it jumps to position 0 and these assertions fail.
 *
 * Run: node scripts/sort-check.ts     (Node >=23 strips the types natively)
 */
import assert from "node:assert/strict";
import { sortStartups, type SortKey } from "../frontend/lib/search.ts";
import type { Startup } from "../frontend/lib/types.ts";

const row = (over: Partial<Startup>): Startup =>
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

// Dead, yet the front-runner by every other measure.
const aardvark = row({
  id: 1,
  name: "Aardvark",
  status: "dead",
  created_at: "2026-06-01T00:00:00Z",
  founded: "2025-01-01",
  stars: 9999,
});
const beta = row({
  id: 2,
  name: "Beta",
  verified: 1,
  verified_at: "2026-05-01T00:00:00Z",
  created_at: "2026-03-01T00:00:00Z",
  founded: "2015-01-01",
  stars: 5,
});
const charlie = row({
  id: 3,
  name: "Charlie",
  created_at: "2026-02-01T00:00:00Z",
  founded: "2020-01-01",
  stars: 50,
});
// Pivoted = tombstone too (half of DEAD_ORDER was untested — Phase 12 gives
// the predicate a second implementation in SQL, so both halves must hold).
const pivoted = row({
  id: 4,
  name: "Pivoted",
  status: "pivoted",
  created_at: "2026-04-01T00:00:00Z",
  founded: "2018-01-01",
  stars: 900,
});

const input = [aardvark, beta, charlie, pivoted];
const KEYS: SortKey[] = ["top", "newest", "verified", "name", "founded"];

let failures = 0;
const check = (label: string, fn: () => void) => {
  try {
    fn();
    console.log(`[PASS] ${label}`);
  } catch (err) {
    failures++;
    console.log(`[FAIL] ${label} — ${err instanceof Error ? err.message : String(err)}`);
  }
};

// The regression itself: BOTH tombstone kinds sink under EVERY key (input
// order preserved among equal-key elements — dead then pivoted at the end).
for (const key of KEYS) {
  check(`sort=${key} sinks dead+pivoted entries to the bottom`, () => {
    const names = sortStartups(input, key).map((s) => s.name);
    assert.deepEqual(names.slice(-2), ["Aardvark", "Pivoted"], `got ${JSON.stringify(names)}`);
  });
}

// And the requested ordering still applies among the live entries.
const live = (key: SortKey) =>
  sortStartups(input, key)
    .filter((s) => s.status !== "dead" && s.status !== "pivoted")
    .map((s) => s.name);

check("sort=name orders live entries alphabetically", () =>
  assert.deepEqual(live("name"), ["Beta", "Charlie"]),
);
check("sort=newest orders live entries by created_at desc", () =>
  assert.deepEqual(live("newest"), ["Beta", "Charlie"]),
);
check("sort=founded orders live entries by founded desc", () =>
  assert.deepEqual(live("founded"), ["Charlie", "Beta"]),
);
check("sort=top puts verified ahead of higher-starred unverified", () =>
  assert.deepEqual(live("top"), ["Beta", "Charlie"]),
);
check("sortStartups does not mutate its input", () =>
  assert.deepEqual(input.map((s) => s.name), ["Aardvark", "Beta", "Charlie", "Pivoted"]),
);

console.log();
if (failures > 0) {
  console.log(`RESULT: ${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("RESULT: ALL PASS");
