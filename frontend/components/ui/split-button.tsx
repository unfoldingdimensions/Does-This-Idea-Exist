"use client";

import { type JSX, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Split button — the main action morphs into a row of options.
 * Adapted from Watermelon UI (MIT): @hugeicons → lucide (one icon set per app),
 * bouncy spring → ease-out (antislop: bounce is banned), tokens → glass.
 * The option row is unmounted when closed (AnimatePresence) so hidden options
 * are never focusable or announced.
 */
export interface SplitButtonOption {
  label: string;
  icon: JSX.Element;
  onClick: () => void;
}

export interface SplitButtonProps {
  mainLabel: string;
  options: SplitButtonOption[];
}

import { EASE } from "@/lib/motion";

export function SplitButton({ mainLabel, options }: SplitButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative flex h-9 items-center justify-center">
      {/* Main button — in flow so the wrapper keeps its width (an absolute
          button collapsed the wrapper to ~0 and overflowed onto the theme
          toggle; see fix batch). */}
      <motion.button
        type="button"
        onClick={() => setOpen(true)}
        className="relative z-10 flex h-9 items-center gap-1.5 whitespace-nowrap rounded-full bg-primary px-4 text-xs font-semibold text-primary-foreground"
        initial={false}
        animate={open ? { opacity: 0, scale: 0.85, filter: "blur(4px)", pointerEvents: "none" as const } : { opacity: 1, scale: 1, filter: "blur(0px)", pointerEvents: "auto" as const }}
        transition={{ type: "tween", ease: EASE, duration: 0.3 }}
      >
        <Plus className="h-3.5 w-3.5" /> {mainLabel}
      </motion.button>

      {/* Split row — mounted only while open; anchored to the right edge so
          it expands leftward and never covers the theme toggle beside it. */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.85, filter: "blur(4px)" }}
            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, scale: 0.85, filter: "blur(4px)" }}
            transition={{ type: "tween", ease: EASE, duration: 0.3 }}
            className="absolute right-0 z-0 flex items-center gap-1.5"
          >
            <motion.button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Cancel"
              title="Cancel"
              className="glass flex h-9 w-9 items-center justify-center rounded-full text-foreground hover:bg-accent"
              whileTap={{ scale: 0.92 }}
              transition={{ type: "tween", ease: EASE, duration: 0.15 }}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
            </motion.button>
            {options.map((opt) => (
              <motion.button
                key={opt.label}
                type="button"
                onClick={() => {
                  setOpen(false);
                  opt.onClick();
                }}
                className={cn(
                  "glass flex h-9 items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 text-xs font-medium text-foreground hover:bg-accent",
                )}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: "tween", ease: EASE, duration: 0.15 }}
              >
                {opt.icon} {opt.label}
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
