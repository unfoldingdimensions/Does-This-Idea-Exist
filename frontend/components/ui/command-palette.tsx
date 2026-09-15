"use client";

import * as React from "react";
import { AnimatePresence, motion } from "motion/react";
import { Search, Command, ArrowRight, Volume2, Table, X } from "lucide-react";
import { sound } from "@/lib/sound-engine";
import type { Startup } from "@/lib/types";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  startups: Startup[];
  onSelectStartup: (startup: Startup) => void;
  onToggleDensity?: () => void;
  onToggleSound?: () => void;
}

export function CommandPalette({
  open,
  onOpenChange,
  startups,
  onSelectStartup,
  onToggleDensity,
  onToggleSound,
}: CommandPaletteProps) {
  const [query, setQuery] = React.useState("");
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Global keyboard shortcut listener for Cmd+K / Ctrl+K
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  // Focus input on open
  React.useEffect(() => {
    if (open) {
      void Promise.resolve().then(() => {
        setQuery("");
        setSelectedIndex(0);
      });
      setTimeout(() => inputRef.current?.focus(), 50);
      sound.playSwoosh();
    }
  }, [open]);

  // Filter items
  const filteredStartups = React.useMemo(() => {
    if (!query.trim()) {
      return startups.slice(0, 8);
    }
    const q = query.toLowerCase().trim();
    return startups
      .filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.category?.toLowerCase().includes(q) ||
          s.description?.toLowerCase().includes(q)
      )
      .slice(0, 10);
  }, [startups, query]);

  // Quick commands
  const quickActions = React.useMemo(() => {
    if (query.trim()) return [];
    return [
      {
        id: "density",
        label: "Switch View Density (Gallery / Ledger)",
        icon: Table,
        action: () => {
          onToggleDensity?.();
          onOpenChange(false);
        },
      },
      {
        id: "sound",
        label: "Toggle Mechanical Audio Synthesis",
        icon: Volume2,
        action: () => {
          onToggleSound?.();
          onOpenChange(false);
        },
      },
    ];
  }, [query, onToggleDensity, onToggleSound, onOpenChange]);

  const totalItems = quickActions.length + filteredStartups.length;

  // Arrow navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = prev < totalItems - 1 ? prev + 1 : 0;
        sound.playTick();
        return next;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = prev > 0 ? prev - 1 : totalItems - 1;
        sound.playTick();
        return next;
      });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex < quickActions.length) {
        quickActions[selectedIndex].action();
      } else {
        const startupIndex = selectedIndex - quickActions.length;
        const selected = filteredStartups[startupIndex];
        if (selected) {
          sound.playChime();
          onSelectStartup(selected);
          onOpenChange(false);
        }
      }
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 sm:pt-28 px-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => onOpenChange(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            aria-hidden="true"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ type: "spring", stiffness: 350, damping: 28 }}
            className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-border/60 bg-popover/95 text-popover-foreground shadow-2xl backdrop-blur-xl ring-1 ring-white/10"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette quick navigation"
          >
            {/* Header Search Bar */}
            <div className="flex items-center border-b border-border/50 px-4 py-3">
              <Search className="mr-3 size-4 shrink-0 text-muted-foreground" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Search startups, categories, founders..."
                className="flex h-6 w-full bg-transparent text-sm placeholder:text-muted-foreground/60 focus:outline-hidden text-foreground"
              />
              <div className="flex items-center gap-1.5 ml-2">
                <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border/60 bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  ESC
                </kbd>
                <button
                  type="button"
                  onClick={() => onOpenChange(false)}
                  className="p-1 rounded-md text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  aria-label="Close command palette"
                >
                  <X className="size-4" />
                </button>
              </div>
            </div>

            {/* Content List */}
            <div className="max-h-80 overflow-y-auto p-2 archival-scrollbar">
              {/* Quick Actions */}
              {quickActions.length > 0 && (
                <div className="mb-2">
                  <div className="px-3 py-1 font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                    Quick Commands
                  </div>
                  {quickActions.map((action, i) => {
                    const isSelected = selectedIndex === i;
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.id}
                        type="button"
                        onClick={action.action}
                        onMouseEnter={() => setSelectedIndex(i)}
                        className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs transition-colors cursor-pointer ${
                          isSelected ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-muted/50"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon className="size-3.5" />
                          <span className="font-medium text-foreground">{action.label}</span>
                        </div>
                        <ArrowRight className="size-3 opacity-60" />
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Startups List */}
              <div>
                <div className="px-3 py-1 font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                  {query ? `Matching Startups (${filteredStartups.length})` : "Featured Archival Entries"}
                </div>
                {filteredStartups.length === 0 ? (
                  <div className="px-4 py-8 text-center text-xs text-muted-foreground">
                    No startups match &ldquo;{query}&rdquo;
                  </div>
                ) : (
                  filteredStartups.map((startup, i) => {
                    const actualIndex = quickActions.length + i;
                    const isSelected = selectedIndex === actualIndex;
                    return (
                      <button
                        key={startup.id || startup.name}
                        type="button"
                        onClick={() => {
                          sound.playChime();
                          onSelectStartup(startup);
                          onOpenChange(false);
                        }}
                        onMouseEnter={() => setSelectedIndex(actualIndex)}
                        className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs transition-colors cursor-pointer ${
                          isSelected ? "bg-accent text-accent-foreground" : "hover:bg-muted/50"
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary font-mono font-semibold text-xs border border-primary/20">
                            {startup.name.charAt(0)}
                          </div>
                          <div className="flex flex-col items-start truncate">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-foreground">{startup.name}</span>
                              {startup.category && (
                                <span className="rounded bg-muted px-1.5 py-0.2 text-[10px] text-muted-foreground font-mono">
                                  {startup.category}
                                </span>
                              )}
                            </div>
                            {startup.description && (
                              <span className="text-[11px] text-muted-foreground truncate max-w-sm text-left">
                                {startup.description}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {startup.verified && (
                            <span className="text-[10px] font-mono text-emerald-500">
                              ✓ VERIFIED
                            </span>
                          )}
                          <ArrowRight className="size-3 text-muted-foreground opacity-60" />
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Footer Status Tip */}
            <div className="flex items-center justify-between border-t border-border/40 bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground font-mono">
              <div className="flex items-center gap-3">
                <span>Navigate <kbd className="font-sans">↑↓</kbd></span>
                <span>Select <kbd className="font-sans">↵</kbd></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Command className="size-3" />
                <span>IDEAEXISTS VAULT</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
