"use client";

import * as React from "react";
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

interface HolographicCardProps {
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

/**
 * HolographicCard — wraps content in an elite 3D physical glass slab.
 * Features:
 * - Multi-axis spring tilt with perspective
 * - Raytraced specular sheen overlay
 * - Iridescent border highlight
 * - Hardware-accelerated GPU transforms
 */
export function HolographicCard({
  children,
  className,
  disabled = false,
}: HolographicCardProps) {
  const reduce = useReducedMotion();
  const cardRef = React.useRef<HTMLDivElement>(null);
  const sheenRef = React.useRef<HTMLDivElement>(null);

  const rawX = useMotionValue(0.5);
  const rawY = useMotionValue(0.5);

  const springCfg = { damping: 26, stiffness: 220, mass: 0.5 };
  const smoothX = useSpring(rawX, springCfg);
  const smoothY = useSpring(rawY, springCfg);

  // 3D rotation angles
  const rotateX = useTransform(smoothY, [0, 1], [6, -6]);
  const rotateY = useTransform(smoothX, [0, 1], [-6, 6]);

  // Specular sheen light position
  const sheenX = useTransform(smoothX, [0, 1], ["0%", "100%"]);
  const sheenY = useTransform(smoothY, [0, 1], ["0%", "100%"]);

  const [hovering, setHovering] = React.useState(false);
  const sheenOpacity = useSpring(hovering ? 1 : 0, { damping: 20, stiffness: 180 });

  React.useEffect(() => {
    if (reduce || disabled) return;
    const el = sheenRef.current;
    if (!el) return;
    const unsubX = sheenX.on("change", (v) => el.style.setProperty("--sheen-x", v));
    const unsubY = sheenY.on("change", (v) => el.style.setProperty("--sheen-y", v));
    return () => {
      unsubX();
      unsubY();
    };
  }, [reduce, disabled, sheenX, sheenY]);

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reduce || disabled || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width;
    const ny = (e.clientY - rect.top) / rect.height;
    rawX.set(nx);
    rawY.set(ny);
  };

  const onMouseEnter = () => {
    if (!reduce && !disabled) setHovering(true);
  };

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
              transformPerspective: 1100,
              transformStyle: "preserve-3d",
            }
      }
      className={cn("group/holo relative h-full transition-shadow duration-300", className)}
    >
      {/* Dynamic Specular Sheen Layer */}
      {!reduce && !disabled && (
        <motion.div
          ref={sheenRef}
          aria-hidden
          className="pointer-events-none absolute inset-0 z-20 rounded-[inherit] overflow-hidden"
          style={{ opacity: sheenOpacity }}
        >
          <div
            className="absolute -inset-[50%] h-[200%] w-[200%]"
            style={{
              background:
                "radial-gradient(circle 240px at var(--sheen-x, 50%) var(--sheen-y, 50%), rgba(255,255,255,0.18) 0%, rgba(255,235,210,0.06) 40%, transparent 70%)",
            }}
          />
          {/* Subtle iridescent edge caustic */}
          <div className="absolute inset-0 rounded-[inherit] border border-white/25 dark:border-white/10 opacity-70" />
        </motion.div>
      )}

      {/* Internal Content with Z-Space Preservation */}
      <div
        className={cn(
          "h-full w-full",
          !reduce && !disabled && "[transform-style:preserve-3d]",
        )}
      >
        {children}
      </div>
    </motion.div>
  );
}
