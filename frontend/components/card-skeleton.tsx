/**
 * CardSkeleton — a skeleton that mirrors real card anatomy (avatar, header
 * lines, pill, tagline/description bars, badges, actions) with the real card's
 * min-height (304px, measured), so the loading→loaded swap never shifts layout
 * (a CLS guard). Deliberately NOT .glass: 12 backdrop-filter surfaces during
 * the LCP window are the most expensive thing on the page and buy nothing
 * behind a placeholder. One composited translateX sweep (skeleton-sweep),
 * killed by the reduced-motion CSS block.
 */
export function CardSkeleton() {
  return (
    <div
      aria-hidden
      className="relative overflow-hidden rounded-2xl border border-border/40 bg-background/45 p-4"
      style={{ minHeight: 304 }}
    >
      {/* Sweep — composited, never background-position. */}
      <span className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 animate-[skeleton-sweep_1.2s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-foreground/5 to-transparent" />

      {/* Header row: avatar + name/meta lines + pill */}
      <div className="flex items-center gap-2.5">
        <div className="size-8 shrink-0 rounded-md bg-foreground/8" />
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="h-3 w-2/3 rounded-full bg-foreground/8" />
          <div className="h-2.5 w-1/2 rounded-full bg-foreground/6" />
        </div>
        <div className="h-5 w-20 shrink-0 rounded-full bg-foreground/6" />
      </div>

      {/* Tagline + description bars */}
      <div className="mt-4 space-y-2">
        <div className="h-3 w-11/12 rounded-full bg-foreground/6" />
        <div className="h-3 w-4/5 rounded-full bg-foreground/6" />
        <div className="h-3 w-2/3 rounded-full bg-foreground/6" />
      </div>

      {/* Footer badges + action pills */}
      <div className="mt-6 flex items-center gap-1.5">
        <div className="h-5 w-16 rounded-full bg-foreground/6" />
        <div className="h-5 w-14 rounded-full bg-foreground/6" />
        <div className="ml-auto flex gap-2">
          <div className="h-8 w-20 rounded-xl bg-foreground/6" />
          <div className="h-8 w-16 rounded-xl bg-foreground/6" />
        </div>
      </div>
    </div>
  );
}
