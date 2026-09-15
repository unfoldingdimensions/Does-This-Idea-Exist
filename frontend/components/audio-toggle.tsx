"use client";

import * as React from "react";
import { Volume2, VolumeX } from "lucide-react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

export function AudioToggle({ className }: { className?: string }) {
  const muted = React.useSyncExternalStore(
    (onStoreChange) => sound.subscribe(onStoreChange),
    () => sound.isMuted(),
    () => true,
  );
  const [pulsing, setPulsing] = React.useState(false);

  const handleToggle = () => {
    const next = sound.toggleMute();
    if (!next) {
      setPulsing(true);
      setTimeout(() => setPulsing(false), 400);
    }
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label={muted ? "Enable audio haptics" : "Mute audio haptics"}
      title={muted ? "Audio: Muted (click to enable tactile sound effects)" : "Audio: Active (click to mute)"}
      className={cn(
        "relative flex h-8 w-8 items-center justify-center rounded-full border border-border/40 bg-background/50 backdrop-blur-md transition-all duration-200 hover:border-primary/50 hover:bg-accent/60 active:scale-95",
        !muted && "border-primary/40 text-primary shadow-[0_0_12px_rgba(var(--primary),0.2)]",
        className,
      )}
    >
      {muted ? (
        <VolumeX className="h-3.5 w-3.5 text-muted-foreground transition-transform duration-200" />
      ) : (
        <Volume2 className={cn("h-3.5 w-3.5 text-primary transition-transform duration-200", pulsing && "scale-125")} />
      )}
      {!muted && (
        <span
          className="absolute -right-0.5 -top-0.5 flex h-2 w-2"
          aria-hidden
        >
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
        </span>
      )}
    </button>
  );
}
