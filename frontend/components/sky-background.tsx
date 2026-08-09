"use client";

import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";

/**
 * The Sky — a fixed, scroll-linked background behind the archive.
 *
 * Light mode: a sunset archive. The warm-paper dawn sinks through amber into a
 * rose dusk as you scroll (the sun glow drifts down and dims, the dusk band
 * deepens). Dark mode: a moon night — the wash sinks from warm charcoal into
 * deep indigo, the moon rises slightly and a sparse star field drifts up.
 *
 * The whole sky is a single `pointer-events-none` layer at z-[-1]: it never
 * blocks interaction and never needs scroll-lock coordination. Both theme
 * washes are mounted and CSS-gated by `.dark`, so the theme toggle crossfades
 * the sky exactly like the rest of the app. All color lives in the --sky-*
 * tokens (globals.css) — this file holds no color literals.
 *
 * Motion discipline: transform/opacity only, ease-out, small amplitudes
 * (≤22vh of travel), and zero motion under prefers-reduced-motion.
 */
export function SkyBackground() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();

  // Sunset (light): the sun sinks toward the horizon as you scroll — it
  // travels far enough to actually read as "going down" — and stays hot
  // (warm gold, not cooling off). The yellow dawn wash crossfades into the
  // orange evening wash so the whole sky shifts tone as the archive deepens.
  const sunY = useTransform(scrollYProgress, [0, 1], ["0vh", "36vh"]);
  const sunO = useTransform(scrollYProgress, [0, 0.5, 1], [1, 0.98, 0.92]);
  const eveningO = useTransform(scrollYProgress, [0, 0.35, 1], [0, 0.75, 1]);
  // The dusk band deepens — the archive darkens toward evening.
  const duskO = useTransform(scrollYProgress, [0, 0.4, 1], [0.45, 0.75, 1]);
  // The horizon finale: the mountain ridge / ocean silhouette rises into
  // view over the final stretch of the page.
  const silhouetteO = useTransform(scrollYProgress, [0.45, 1], [0, 1]);

  // Night (dark): the moon sinks toward the ridge as you scroll, setting
  // behind the mountains at the bottom of the page exactly like the sun does
  // in light mode. It brightens a touch as it descends (atmospheric glow).
  const moonY = useTransform(scrollYProgress, [0, 1], ["0vh", "42vh"]);
  const moonO = useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 0.92, 1]);
  const starO = useTransform(scrollYProgress, [0, 0.3, 1], [0.15, 0.6, 0.9]);

  // Deterministic star positions (SSR == client, no hydration mismatch).
  const stars = [
    { top: "5%", left: "9%", size: 2 },
    { top: "9%", left: "84%", size: 2 },
    { top: "14%", left: "26%", size: 1.5 },
    { top: "17%", left: "62%", size: 2 },
    { top: "24%", left: "5%", size: 1.5 },
    { top: "28%", left: "92%", size: 2 },
    { top: "33%", left: "42%", size: 1.5 },
    { top: "38%", left: "74%", size: 1.5 },
    { top: "44%", left: "16%", size: 2 },
    { top: "48%", left: "56%", size: 1.5 },
    { top: "54%", left: "88%", size: 1.5 },
    { top: "58%", left: "33%", size: 2 },
  ];

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[-1] overflow-hidden"
    >
      {/* Sunset wash — visible in light mode, fades out under .dark */}
      <div className="absolute inset-0 transition-opacity duration-700 dark:opacity-0">
        <div className="sky-wash-sunset absolute inset-0" />
        {/* Evening wash — crossfades in over the dawn as you scroll, shifting
            the sky from yellow-gold to orange. Reduced motion: held at a
            mid-glow so the sunset still reads, just without the travel. */}
        <motion.div
          className="sky-wash-evening absolute inset-0"
          style={{ opacity: reduce ? 0.6 : eveningO }}
        />
        <motion.div
          className="sky-sun"
          style={{
            top: "26vh",
            left: "18vw",
            y: reduce ? 0 : sunY,
            opacity: reduce ? 1 : sunO,
          }}
        />
        <motion.div
          className="sky-dusk"
          style={{ opacity: reduce ? 0.75 : duskO }}
        />
      </div>

      {/* Moon-night wash — hidden in light mode, fades in under .dark */}
      <div className="absolute inset-0 opacity-0 transition-opacity duration-700 dark:opacity-100">
        <div className="sky-wash-night absolute inset-0" />
        <motion.div
          className="sky-moon"
          style={{
            top: "12vh",
            right: "14vw",
            y: reduce ? 0 : moonY,
            opacity: reduce ? 0.95 : moonO,
          }}
        />
        <motion.div
          className="absolute inset-0"
          style={{ opacity: reduce ? 0.6 : starO }}
        >
          {stars.map((s, i) => (
            <span
              key={i}
              className="sky-star"
              style={{
                top: s.top,
                left: s.left,
                width: s.size,
                height: s.size,
              }}
            />
          ))}
        </motion.div>
      </div>

      {/* Mountain ridge — shared by both themes: the sun settles behind it in
          light mode, it frames the moon-lit sky in dark mode. Fades in over
          the final stretch of the page. */}
      <motion.div
        className="sky-silhouette sky-silhouette--mountain"
        style={{ opacity: reduce ? 1 : silhouetteO }}
      />
    </div>
  );
}
