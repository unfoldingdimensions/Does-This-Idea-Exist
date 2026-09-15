"use client";

import * as React from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { ShieldCheck, Archive } from "lucide-react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

interface StampChoreographyProps {
  type: "verified" | "dead" | null;
  onComplete?: () => void;
  className?: string;
}

export function StampChoreography({ type, onComplete, className }: StampChoreographyProps) {
  const reduce = useReducedMotion();

  React.useEffect(() => {
    if (type) {
      sound.playStamp();
      if (type === "verified") {
        setTimeout(() => sound.playChime(), 140);
      }
      const timer = setTimeout(() => {
        onComplete?.();
      }, 1600);
      return () => clearTimeout(timer);
    }
  }, [type, onComplete]);

  if (!type) return null;

  return (
    <AnimatePresence>
      <div
        className={cn(
          "pointer-events-none absolute inset-0 z-30 flex items-center justify-center overflow-hidden rounded-[inherit]",
          className,
        )}
      >
        {/* Shockwave ripple ring */}
        {!reduce && (
          <motion.div
            initial={{ scale: 0.2, opacity: 0.9 }}
            animate={{ scale: 2.2, opacity: 0 }}
            transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              "absolute h-32 w-32 rounded-full border-2",
              type === "verified" ? "border-success/60 bg-success/15" : "border-destructive/60 bg-destructive/15",
            )}
          />
        )}

        {/* Floating stardust glitter burst for Verified */}
        {!reduce && type === "verified" && (
          <div className="absolute inset-0 flex items-center justify-center">
            {Array.from({ length: 8 }).map((_, i) => {
              const angle = (i * 45 * Math.PI) / 180;
              const dist = 60 + (i % 2) * 20;
              const tx = Math.cos(angle) * dist;
              const ty = Math.sin(angle) * dist;
              return (
                <motion.div
                  key={i}
                  initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
                  animate={{ x: tx, y: ty, scale: 0, opacity: 0 }}
                  transition={{ duration: 0.75, delay: 0.05, ease: "easeOut" }}
                  className="absolute h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]"
                />
              );
            })}
          </div>
        )}

        {/* Slamming Rubber Stamp Impression */}
        <motion.div
          initial={reduce ? { opacity: 0 } : { scale: 2.5, rotate: -24, opacity: 0 }}
          animate={{ scale: 1, rotate: -8, opacity: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={
            reduce
              ? { duration: 0.2 }
              : {
                  type: "spring",
                  stiffness: 420,
                  damping: 18,
                  mass: 0.6,
                }
          }
          className={cn(
            "relative flex items-center gap-2 rounded-xl border-2 px-4 py-2 font-mono text-xs font-black uppercase tracking-[0.22em] shadow-2xl backdrop-blur-md",
            type === "verified"
              ? "border-success bg-success/20 text-success shadow-success/30"
              : "border-destructive bg-destructive/20 text-destructive shadow-destructive/30",
          )}
        >
          {type === "verified" ? (
            <>
              <ShieldCheck className="h-4 w-4 stroke-[2.5]" />
              <span>Verified Alive</span>
            </>
          ) : (
            <>
              <Archive className="h-4 w-4 stroke-[2.5]" />
              <span>Filed to Vault</span>
            </>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
