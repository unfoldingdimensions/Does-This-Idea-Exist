"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

/**
 * Single-button light/dark toggle. The icon renders only on the client:
 * `resolvedTheme` is undefined during SSR, so rendering the icon directly
 * causes a hydration mismatch (server: Moon, client: Sun). `useSyncExternalStore`
 * detects client mount without an effect (react-hooks v7 bans set-state-in-effect).
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
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
      className="glass size-9 rounded-full"
    >
      {!isClient ? (
        <span className="size-4" aria-hidden />
      ) : isDark ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  );
}
