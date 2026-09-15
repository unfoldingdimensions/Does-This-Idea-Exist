"use client";

import * as React from "react";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  useMotionValue,
  useSpring,
} from "motion/react";

/**
 * The Sky — a fixed, scroll-linked + mouse-parallax background.
 *
 * Light mode: sunset archive with a fully custom SVG sun (disc + rotating rays +
 * corona shimmer + warm glow). Dark mode: moon night with a detailed SVG moon
 * (disc + craters + halo glow + starfield with shooting stars).
 *
 * Mouse parallax: celestial bodies gently drift toward the pointer for ambient
 * life even when the user is not scrolling. Parallax is compositor-friendly
 * (transform only, no layout/paint).
 *
 * Motion discipline: transform/opacity only, ease-out, zero motion under
 * prefers-reduced-motion. All color lives in --sky-* tokens in globals.css.
 */
export function SkyBackground() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();

  // --- Scroll-linked celestial travel ---
  const sunY = useTransform(scrollYProgress, [0, 1], ["0vh", "36vh"]);
  const sunO = useTransform(scrollYProgress, [0, 0.5, 1], [1, 0.98, 0.92]);
  const eveningO = useTransform(scrollYProgress, [0, 0.35, 1], [0, 0.75, 1]);
  const duskO = useTransform(scrollYProgress, [0, 0.4, 1], [0.45, 0.75, 1]);
  const silhouetteO = useTransform(scrollYProgress, [0.45, 1], [0, 1]);
  const moonY = useTransform(scrollYProgress, [0, 1], ["0vh", "42vh"]);
  const moonO = useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 0.92, 1]);
  const starO = useTransform(scrollYProgress, [0, 0.3, 1], [0.15, 0.6, 0.9]);

  // --- Mouse parallax ---
  const rawMouseX = useMotionValue(0);
  const rawMouseY = useMotionValue(0);
  const springConfig = { damping: 50, stiffness: 90, mass: 1.2 };
  const mouseX = useSpring(rawMouseX, springConfig);
  const mouseY = useSpring(rawMouseY, springConfig);

  React.useEffect(() => {
    if (reduce) return;
    const onMove = (e: MouseEvent) => {
      // Normalize to [-1, 1]
      const nx = (e.clientX / window.innerWidth - 0.5) * 2;
      const ny = (e.clientY / window.innerHeight - 0.5) * 2;
      rawMouseX.set(nx * 14); // px shift amplitude
      rawMouseY.set(ny * 10);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [reduce, rawMouseX, rawMouseY]);

  // Deterministic star positions (SSR == client, no hydration mismatch).
  const stars = [
    { top: "5%", left: "9%", size: 2.5, twinkleDelay: 0 },
    { top: "9%", left: "84%", size: 2, twinkleDelay: 0.71 },
    { top: "14%", left: "26%", size: 1.5, twinkleDelay: 1.42 },
    { top: "17%", left: "62%", size: 2.5, twinkleDelay: 2.13 },
    { top: "24%", left: "5%", size: 1.5, twinkleDelay: 0.5 },
    { top: "28%", left: "92%", size: 2, twinkleDelay: 1.21 },
    { top: "33%", left: "42%", size: 1.5, twinkleDelay: 1.92 },
    { top: "38%", left: "74%", size: 2, twinkleDelay: 2.63 },
    { top: "44%", left: "16%", size: 2.5, twinkleDelay: 0.35 },
    { top: "48%", left: "56%", size: 1.5, twinkleDelay: 1.06 },
    { top: "54%", left: "88%", size: 1.5, twinkleDelay: 1.77 },
    { top: "58%", left: "33%", size: 2, twinkleDelay: 2.48 },
    { top: "12%", left: "50%", size: 1.5, twinkleDelay: 3.1 },
    { top: "65%", left: "18%", size: 1.5, twinkleDelay: 0.9 },
    { top: "70%", left: "70%", size: 2, twinkleDelay: 1.6 },
    { top: "7%", left: "39%", size: 1.5, twinkleDelay: 2.3 },
  ];

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[-1] overflow-hidden"
    >
      {/* ── Sunset wash — light mode ── */}
      <div className="absolute inset-0 transition-opacity duration-700 dark:opacity-0">
        <div className="sky-wash-sunset absolute inset-0" />
        <motion.div
          className="sky-wash-evening absolute inset-0"
          style={{ opacity: reduce ? 0.6 : eveningO }}
        />

        {/* Custom SVG Sun */}
        <motion.div
          className="sky-sun absolute"
          style={{
            top: "26vh",
            left: "18vw",
            x: reduce ? 0 : mouseX,
            y: reduce ? 0 : sunY,
            opacity: reduce ? 1 : sunO,
            translateX: "-50%",
            translateY: "-50%",
          }}
        >
          <motion.div style={{ y: reduce ? 0 : mouseY }}>
            <SunSVG reduce={reduce} />
          </motion.div>
        </motion.div>

        <motion.div
          className="sky-dusk"
          style={{ opacity: reduce ? 0.75 : duskO }}
        />
      </div>

      {/* ── Moon night wash — dark mode ── */}
      <div className="absolute inset-0 opacity-0 transition-opacity duration-700 dark:opacity-100">
        <div className="sky-wash-night absolute inset-0" />

        {/* Custom SVG Moon */}
        <motion.div
          className="sky-moon absolute"
          style={{
            top: "12vh",
            right: "14vw",
            x: reduce ? 0 : mouseX,
            y: reduce ? 0 : moonY,
            opacity: reduce ? 0.95 : moonO,
            translateX: "50%",
            translateY: "-50%",
          }}
        >
          <motion.div style={{ y: reduce ? 0 : mouseY }}>
            <MoonSVG reduce={reduce} />
          </motion.div>
        </motion.div>

        {/* Star field */}
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
                ["--twinkle-delay" as string]: `${s.twinkleDelay}s`,
              }}
            />
          ))}
          {/* Shooting star — animates on a long loop */}
          {!reduce && <ShootingStar />}
        </motion.div>
      </div>

      {/* Mountain silhouette — both themes */}
      <motion.div
        className="sky-silhouette sky-silhouette--mountain"
        style={{ opacity: reduce ? 1 : silhouetteO }}
      />

      {/* Paper grain */}
      <div className="sky-grain" aria-hidden />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Custom SVG Sun
   Layers: disc + 8 rays (rotating) + inner corona (pulsing) + outer glow
───────────────────────────────────────────────────────── */
function SunSVG({ reduce }: { reduce: boolean | null }) {
  return (
    <div className="relative" style={{ width: "44vmin", height: "44vmin" }}>
      {/* Outer ambient glow — CSS class drives the radial gradient */}
      <span className="sky-breathe" aria-hidden />

      {/* SVG sun body */}
      <motion.svg
        viewBox="0 0 120 120"
        className="absolute inset-0 h-full w-full"
        aria-hidden
      >
        {/* Soft outer corona */}
        <circle
          cx="60"
          cy="60"
          r="46"
          fill="oklch(0.99 0.09 88 / 0.12)"
        />
        <circle
          cx="60"
          cy="60"
          r="38"
          fill="oklch(0.99 0.1 86 / 0.22)"
        />

        {/* Rotating rays group */}
        <motion.g
          animate={reduce ? {} : { rotate: 360 }}
          transition={reduce ? {} : { repeat: Infinity, duration: 80, ease: "linear" }}
          style={{ originX: "60px", originY: "60px", transformOrigin: "60px 60px" }}
        >
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = (i * 360) / 12;
            const isLong = i % 3 === 0;
            return (
              <line
                key={i}
                x1="60"
                y1={isLong ? 6 : 10}
                x2="60"
                y2={isLong ? 18 : 16}
                stroke={isLong ? "oklch(0.99 0.1 88 / 0.65)" : "oklch(0.98 0.08 86 / 0.38)"}
                strokeWidth={isLong ? 2.5 : 1.5}
                strokeLinecap="round"
                transform={`rotate(${angle} 60 60)`}
              />
            );
          })}
        </motion.g>

        {/* Inner pulsing disc */}
        <motion.circle
          cx="60"
          cy="60"
          r="26"
          fill="oklch(0.99 0.09 88 / 0.9)"
          animate={reduce ? {} : { r: [26, 27.5, 26] }}
          transition={reduce ? {} : { repeat: Infinity, duration: 4, ease: "easeInOut" }}
        />
        {/* Core */}
        <circle cx="60" cy="60" r="18" fill="oklch(1 0.06 90 / 0.97)" />
      </motion.svg>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Custom SVG Moon
   Layers: crescent disc + craters + halo glow + shimmer ring
───────────────────────────────────────────────────────── */
function MoonSVG({ reduce }: { reduce: boolean | null }) {
  return (
    <div className="relative" style={{ width: "24vmin", height: "24vmin" }}>
      {/* Outer halo glow */}
      <span className="sky-breathe" aria-hidden />

      <motion.svg
        viewBox="0 0 100 100"
        className="absolute inset-0 h-full w-full"
        aria-hidden
        animate={reduce ? {} : { rotate: [0, 1.5, -1, 0.5, 0] }}
        transition={reduce ? {} : { repeat: Infinity, duration: 12, ease: "easeInOut" }}
      >
        {/* Outer ambient halo */}
        <circle cx="50" cy="50" r="44" fill="oklch(0.95 0.03 85 / 0.07)" />
        <circle cx="50" cy="50" r="38" fill="oklch(0.95 0.03 85 / 0.12)" />

        {/* Crescent moon via clip: full circle clipped by an offset circle */}
        <defs>
          <clipPath id="moon-crescent">
            <circle cx="50" cy="50" r="28" />
          </clipPath>
        </defs>
        {/* Moon disc */}
        <circle cx="50" cy="50" r="28" fill="oklch(0.93 0.025 82 / 0.92)" />
        {/* Shadow bite — creates crescent effect */}
        <circle cx="61" cy="46" r="23" fill="oklch(0.235 0.014 262 / 0.88)" />

        {/* Craters */}
        <circle cx="38" cy="44" r="3.5" fill="oklch(0.88 0.022 82 / 0.35)" />
        <circle cx="42" cy="56" r="2.2" fill="oklch(0.88 0.022 82 / 0.28)" />
        <circle cx="32" cy="55" r="1.8" fill="oklch(0.88 0.022 82 / 0.2)" />
        <circle cx="45" cy="38" r="1.4" fill="oklch(0.9 0.02 84 / 0.22)" />

        {/* Rim highlight */}
        <circle
          cx="50"
          cy="50"
          r="28"
          fill="none"
          stroke="oklch(0.96 0.03 84 / 0.25)"
          strokeWidth="1"
        />

        {/* Shimmer ring — slow pulsing */}
        <motion.circle
          cx="50"
          cy="50"
          r="32"
          fill="none"
          stroke="oklch(0.95 0.04 85 / 0.15)"
          strokeWidth="2"
          animate={reduce ? {} : { r: [32, 36, 32], opacity: [0.15, 0.05, 0.15] }}
          transition={reduce ? {} : { repeat: Infinity, duration: 5, ease: "easeInOut" }}
        />
      </motion.svg>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Shooting Star — fires every 14–22s on a random diagonal.
   SSR-safe: the position is randomized in a lazy useState
   initializer, but the star renders nothing until the client
   is confirmed via useSyncExternalStore (the same pattern the
   theme toggle uses). Server and first client paint both emit
   null — deterministic — so Math.random() never reaches the
   hydration diff; the star streaks in right after mount.
   (react-hooks v7 bans setState-in-effect, so no mounted
   flag via useState+useEffect.)
────────────────────────────────────────────────────────── */
const emptySubscribe = () => () => {};

function ShootingStar() {
  const [key, setKey] = React.useState(0);
  const isClient = React.useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const [startPos] = React.useState(() => ({
    x: 10 + Math.random() * 50,
    y: 5 + Math.random() * 20,
  }));

  React.useEffect(() => {
    if (!isClient) return;
    const delay = 14000 + Math.random() * 8000;
    const t = setTimeout(() => setKey((k) => k + 1), delay);
    return () => clearTimeout(t);
  }, [isClient, key]);

  if (!isClient) return null;

  return (
    <motion.div
      key={key}
      aria-hidden
      className="pointer-events-none absolute"
      style={{
        top: `${startPos.y}%`,
        left: `${startPos.x}%`,
        width: 80,
        height: 1.5,
        background:
          "linear-gradient(90deg, transparent, oklch(0.95 0.03 85 / 0.9) 60%, transparent)",
        borderRadius: 9999,
        rotate: 25,
      }}
      initial={{ opacity: 0, x: 0, scaleX: 0 }}
      animate={{ opacity: [0, 1, 1, 0], x: 160, scaleX: [0, 1, 1, 0.3] }}
      transition={{ duration: 0.75, ease: "easeOut" }}
    />
  );
}
