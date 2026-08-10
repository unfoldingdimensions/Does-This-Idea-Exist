"use client";

import type Lenis from "lenis";

/**
 * Scroll utilities shared between the Lenis provider and page-level code.
 *
 * Deliberately free of any RUNTIME `lenis` import — the type-only import is
 * erased at compile time, so importing this module never pulls the Lenis
 * library into a bundle. That keeps Lenis out of the critical hydration path:
 * only `LenisProvider` (lazy-loaded) loads it.
 */

/** Module-level handle to the running Lenis instance so page-level code (e.g.
 * pagination scroll-to-top) can drive the same smooth-scroll engine without
 * prop-drilling. Null while reduced motion is on — Lenis is skipped there. */
export const lenisRef: { current: Lenis | null } = { current: null };

/**
 * Smoothly scroll the page to the very top. Instant jump under
 * prefers-reduced-motion; falls back to native smooth scrolling when Lenis
 * isn't active (e.g. SSR-safe guard or reduced-motion user).
 */
export function scrollPageToTop() {
  if (typeof window === "undefined") return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    // Instant jump. If Lenis is somehow still live (reduce toggled mid-session)
    // stop it first — its raf loop fights a raw window.scrollTo and can snap
    // back to the old position. Reduced-motion users don't want Lenis anyway.
    if (lenisRef.current) lenisRef.current.stop();
    window.scrollTo(0, 0);
    return;
  }
  if (lenisRef.current) {
    // easeOutQuint — the app's EASE curve (cubic-bezier(0.22, 1, 0.36, 1)),
    // not Lenis's snappier default, so the page-change glide matches every
    // other motion in the app.
    lenisRef.current.scrollTo(0, {
      duration: 0.8,
      easing: (t) => 1 - Math.pow(1 - t, 5),
    });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}
