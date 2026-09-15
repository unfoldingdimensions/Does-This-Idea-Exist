"use client";

import * as React from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "motion/react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

/**
 * Bespoke celestial theme toggle.
 *
 * Light → Dark: sun rays retract inward while a crescent moon cuts in from the
 * right, then sparks of stardust burst outward and fade.
 * Dark → Light: moon dissolves, rays expand outward as the sun disc brightens.
 *
 * The SVG sun/moon morph entirely in SVG + Framer Motion — no Lucide icons.
 * The button has a magnetic hover pull and a springy tap.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const reduce = useReducedMotion();
  const isClient = React.useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const isDark = isClient && resolvedTheme === "dark";
  const [bursting, setBursting] = React.useState(false);
  const burstTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleToggle = () => {
    setBursting(true);
    setTheme(isDark ? "light" : "dark");
    if (burstTimer.current) clearTimeout(burstTimer.current);
    burstTimer.current = setTimeout(() => setBursting(false), 700);
  };
  React.useEffect(
    () => () => {
      if (burstTimer.current) clearTimeout(burstTimer.current);
    },
    [],
  );

  // Magnetic hover pull — motion values, not state: the old setHoverOffset on
  // every mousemove re-rendered the whole toggle at pointer frequency.
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const magnetX = useSpring(rawX, { stiffness: 300, damping: 28 });
  const magnetY = useSpring(rawY, { stiffness: 300, damping: 28 });
  const btnRef = React.useRef<HTMLButtonElement>(null);

  const onMouseMove = (e: React.MouseEvent) => {
    if (reduce || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    rawX.set((e.clientX - (rect.left + rect.width / 2)) * 0.28);
    rawY.set((e.clientY - (rect.top + rect.height / 2)) * 0.28);
  };

  const onMouseLeave = () => {
    rawX.set(0);
    rawY.set(0);
  };

  return (
    <div className="relative">
      <motion.div style={reduce ? undefined : { x: magnetX, y: magnetY }}>
        <Button
          ref={btnRef}
          variant="ghost"
          size="icon"
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          onClick={handleToggle}
          onMouseMove={onMouseMove}
          onMouseLeave={onMouseLeave}
          className="glass relative size-11 overflow-hidden rounded-full"
        >
          {!isClient ? (
            <span className="size-5" aria-hidden />
          ) : (
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={isDark ? "sun" : "moon"}
                initial={reduce ? false : { opacity: 0, scale: 0.6, rotate: isDark ? -120 : 120 }}
                animate={{ opacity: 1, scale: 1, rotate: 0 }}
                exit={reduce ? undefined : { opacity: 0, scale: 0.6, rotate: isDark ? 120 : -120 }}
                transition={{ type: "spring", stiffness: 400, damping: 26 }}
                className="flex items-center justify-center"
              >
                {isDark ? <SunIcon /> : <MoonIcon />}
              </motion.span>
            </AnimatePresence>
          )}

          {/* Hover glow */}
          <motion.span
            className="pointer-events-none absolute inset-0 rounded-full"
            animate={reduce ? {} : {
              background: isDark
                ? "radial-gradient(circle, oklch(0.99 0.09 88 / 0.15) 0%, transparent 70%)"
                : "radial-gradient(circle, oklch(0.95 0.03 85 / 0.18) 0%, transparent 70%)",
            }}
            transition={{ duration: 0.3 }}
          />
        </Button>
      </motion.div>

      {/* Stardust burst on toggle */}
      {!reduce && bursting && <StarburstParticles isDark={isDark} />}
    </div>
  );
}

/* ── Sun icon (compact, 20px viewport) ── */
function SunIcon() {
  return (
    <svg viewBox="0 0 20 20" width={20} height={20} aria-hidden fill="none">
      {/* Rays */}
      {Array.from({ length: 8 }).map((_, i) => {
        const angle = (i * 360) / 8;
        return (
          <motion.line
            key={i}
            x1="10"
            y1="2"
            x2="10"
            y2="4.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            transform={`rotate(${angle} 10 10)`}
            initial={{ scaleY: 0, opacity: 0 }}
            animate={{ scaleY: 1, opacity: 1 }}
            transition={{ delay: i * 0.03, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            style={{ transformOrigin: "10px 10px" }}
          />
        );
      })}
      {/* Disc */}
      <motion.circle
        cx="10"
        cy="10"
        r="3.8"
        fill="currentColor"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 450, damping: 22 }}
        style={{ transformOrigin: "10px 10px" }}
      />
    </svg>
  );
}

/* ── Moon icon (crescent, 20px viewport) ── */
function MoonIcon() {
  return (
    <svg viewBox="0 0 20 20" width={20} height={20} aria-hidden fill="none">
      <defs>
        <mask id="toggle-moon-mask">
          <rect width="20" height="20" fill="white" />
          <motion.circle
            cx="13.5"
            cy="9"
            r="5.8"
            fill="black"
            initial={{ x: -8 }}
            animate={{ x: 0 }}
            transition={{ type: "spring", stiffness: 380, damping: 28, delay: 0.06 }}
          />
        </mask>
      </defs>
      <motion.circle
        cx="10"
        cy="10"
        r="7"
        fill="currentColor"
        mask="url(#toggle-moon-mask)"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 420, damping: 24 }}
        style={{ transformOrigin: "10px 10px" }}
      />
      {/* Small star dot near moon */}
      <motion.circle
        cx="16"
        cy="5"
        r="0.9"
        fill="currentColor"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 0.7 }}
        transition={{ delay: 0.2, duration: 0.3 }}
        style={{ transformOrigin: "16px 5px" }}
      />
    </svg>
  );
}

/* ── Stardust burst on toggle click (deterministic particles) ── */
const PARTICLES = [
  { id: 0, tx: 24, ty: 0, size: 2.8 },
  { id: 1, tx: 18, ty: 18, size: 2.2 },
  { id: 2, tx: 0, ty: 26, size: 3.2 },
  { id: 3, tx: -19, ty: 19, size: 2.0 },
  { id: 4, tx: -25, ty: 0, size: 2.6 },
  { id: 5, tx: -17, ty: -17, size: 3.0 },
  { id: 6, tx: 0, ty: -24, size: 2.2 },
  { id: 7, tx: 18, ty: -18, size: 2.4 },
];

function StarburstParticles({ isDark }: { isDark: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden>
      {PARTICLES.map((p) => (
        <motion.span
          key={p.id}
          className="absolute rounded-full"
          style={{
            width: p.size,
            height: p.size,
            background: isDark
              ? "oklch(0.99 0.09 88 / 0.9)"
              : "oklch(0.95 0.03 85 / 0.85)",
          }}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
          animate={{ x: p.tx, y: p.ty, opacity: 0, scale: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        />
      ))}
    </div>
  );
}
