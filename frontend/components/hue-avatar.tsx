"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/lib/initials";
import { hueAvatarStyle } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Deterministic-hue initial avatar — the card's color identity.
 * Renders identically in both themes (pastel chip + dark letter).
 */
export function HueAvatar({
  name,
  size = "md",
  className,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  return (
    <Avatar
      className={cn(
        "shrink-0 rounded-md bg-muted",
        size === "sm" && "size-6 text-[10px]",
        size === "md" && "size-8 text-xs",
        size === "lg" && "size-12 text-base",
        className,
      )}
    >
      <AvatarFallback className="rounded-md font-bold" style={hueAvatarStyle(name)}>
        {initials(name)}
      </AvatarFallback>
    </Avatar>
  );
}
