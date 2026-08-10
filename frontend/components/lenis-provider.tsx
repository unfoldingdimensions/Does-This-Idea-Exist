"use client";

import * as React from "react";
import Lenis from "lenis";
import { lenisRef } from "./scroll-utils";

/**
 * Inertial smooth scrolling via Lenis — the "fluid" feel for the one-pager.
 * Skipped entirely under prefers-reduced-motion. Stops/starts in sync with
 * the app's modal scroll-lock (modals set body.style.overflow = "hidden"),
 * so Lenis never fights a locked page.
 *
 * Lazy-loaded from `layout.tsx` (`next/dynamic`, ssr:false) so the Lenis
 * library stays out of the critical hydration path; the shared
 * `scrollPageToTop`/`lenisRef` helpers live in `scroll-utils.ts` and carry
 * no runtime `lenis` import.
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
