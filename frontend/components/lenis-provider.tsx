"use client";

import * as React from "react";
import Lenis from "lenis";

/**
 * Module-level handle to the running Lenis instance so page-level code (e.g.
 * pagination scroll-to-top) can drive the same smooth-scroll engine without
 * prop-drilling. Null while reduced motion is on — Lenis is skipped there.
 */
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

/**
 * Inertial smooth scrolling via Lenis — the "fluid" feel for the one-pager.
 * Skipped entirely under prefers-reduced-motion. Stops/starts in sync with
 * the app's modal scroll-lock (modals set body.style.overflow = "hidden"),
 * so Lenis never fights a locked page.
 */
export function LenisProvider({ children }: { children: React.ReactNode }) {
  React.useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const lenis = new Lenis({
      lerp: 0.09,
      smoothWheel: true,
      wheelMultiplier: 1,
    });
    lenisRef.current = lenis;

    let rafId = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    };
    rafId = requestAnimationFrame(raf);

    // Sync with the body scroll-lock used by the modals.
    const sync = () => {
      const locked = document.body.style.overflow === "hidden";
      if (locked) lenis.stop();
      else lenis.start();
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { attributes: true, attributeFilter: ["style"] });
    sync();

    return () => {
      cancelAnimationFrame(rafId);
      observer.disconnect();
      lenis.destroy();
      lenisRef.current = null;
    };
  }, []);

  return <>{children}</>;
}
