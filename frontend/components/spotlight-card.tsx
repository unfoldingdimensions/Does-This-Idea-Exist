"use client";

import * as React from "react";
import { motion, useMotionValue, useTransform, useSpring, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * SpotlightCard — wraps any content in a glass card that reacts to mouse
 * position with a radial spotlight following the pointer along the border
 * (the "lit glass rim" effect) plus a subtle 3D tilt.
 *
 * Only the border highlight and tilt move — the card's own content, z-index
 * stacking, and layout are untouched. compositor-friendly: transform + opacity only.
 */
export function SpotlightCard({
  children,
  className,
  disabled = false,
}: {
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  const reduce = useReducedMotion();
  const cardRef = React.useRef<HTMLDivElement>(null);

  const rawX = useMotionValue(0.5);
  const rawY = useMotionValue(0.5);

  const springCfg = { damping: 30, stiffness: 200, mass: 0.6 };
  const x = useSpring(rawX, springCfg);
  const y = useSpring(rawY, springCfg);

  // 3D tilt — max ±5 degrees
  const rotateX = useTransform(y, [0, 1], [4, -4]);
  const rotateY = useTransform(x, [0, 1], [-4, 4]);

  // Spotlight position as CSS background-position percentages
  const spotX = useTransform(x, [0, 1], ["0%", "100%"]);
  const spotY = useTransform(y, [0, 1], ["0%", "100%"]);

  // Spotlight opacity — 0 at rest, 1 when hovering
  const [hovering, setHovering] = React.useState(false);
  const spotO = useSpring(hovering ? 1 : 0, { damping: 20, stiffness: 180 });

  const spotlightRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (reduce || disabled) return;
    const el = spotlightRef.current;
    if (!el) return;
    const unsubX = spotX.on("change", (v) => el.style.setProperty("--spot-x", v));
    const unsubY = spotY.on("change", (v) => el.style.setProperty("--spot-y", v));
    return () => {
      unsubX();
      unsubY();
    };
  }, [reduce, disabled, spotX, spotY]);

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reduce || disabled || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    rawX.set((e.clientX - rect.left) / rect.width);
    rawY.set((e.clientY - rect.top) / rect.height);
  };

  const onMouseEnter = () => { if (!reduce && !disabled) setHovering(true); };
  const onMouseLeave = () => {
    setHovering(false);
    rawX.set(0.5);
    rawY.set(0.5);
  };

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={onMouseMove}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={
        reduce || disabled
          ? {}
          : {
              rotateX,
              rotateY,
              transformPerspective: 900,
              transformStyle: "preserve-3d",
            }
      }
      className={cn("relative", className)}
    >
      {/* Rim spotlight — sits on top of the glass surface, below content */}
      {!reduce && !disabled && (
        <motion.div
          ref={spotlightRef}
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
          style={{
            opacity: spotO,
            background: "radial-gradient(circle 120px at var(--spot-x, 50%) var(--spot-y, 50%), oklch(1 0 0 / 0.12) 0%, transparent 70%)",
          }}
        />
      )}
      {children}
    </motion.div>
  );
}
