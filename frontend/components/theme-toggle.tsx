"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Single-button light/dark toggle with a crossfade icon swap. The icon renders
 * only on the client: `resolvedTheme` is undefined during SSR, so rendering the
 * icon directly causes a hydration mismatch (server: Moon, client: Sun).
 * `useSyncExternalStore` detects client mount without an effect (react-hooks v7
 * bans set-state-in-effect).
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

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="glass size-11 rounded-full"
    >
      {!isClient ? (
        <span className="size-4" aria-hidden />
      ) : (
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={isDark ? "sun" : "moon"}
            initial={reduce ? false : { opacity: 0, rotate: -90, scale: 0.5 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={reduce ? undefined : { opacity: 0, rotate: 90, scale: 0.5 }}
            transition={{ type: "tween", ease: EASE, duration: 0.22 }}
            className="flex"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </motion.span>
        </AnimatePresence>
      )}
    </Button>
  );
}
