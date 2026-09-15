import type { Easing, Transition } from "motion/react";

/**
 * The archive's shared motion language — one easing curve, two sanctioned
 * springs, one stagger, one reduced-motion collapse. Every component imports
 * from here instead of writing its own EASE tuple (there were six copies).
 *
 * Contract (DESIGN.md → Motion): ease-out is the default everywhere; springs
 * run only where named (shared-layout pills / admin accordion →
 * SPRING_SETTLE, verify stamp → SPRING_STAMP); nothing springs on hover or
 * on grid entrances; everything collapses to STILL under reduced motion.
 */

/** Exponential ease-out — the default easing for every tween. */
export const EASE = [0.22, 1, 0.36, 1] as const;

/** Default tween duration. */
export const DUR = 0.35;

/** Standard tween transition — the default for everything. */
export const tween = (duration: number = DUR, ease: Easing = EASE): Transition => ({
  type: "tween",
  ease,
  duration,
});

/** Critically damped settle — shared-layout pills + admin accordion. No visible overshoot. */
export const SPRING_SETTLE: Transition = {
  type: "spring",
  stiffness: 500,
  damping: 40,
  mass: 0.8,
};

/** The one sanctioned overshoot — a rubber stamp rebounding off paper. Verify stamp only. */
export const SPRING_STAMP: Transition = {
  type: "spring",
  stiffness: 600,
  damping: 12,
  mass: 0.6,
};
