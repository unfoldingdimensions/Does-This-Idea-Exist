"use client";

import * as React from "react";
import Link from "next/link";
import { FileWarning } from "lucide-react";

/**
 * Themed render-error boundary — without it a runtime error in the page tree
 * fell through to Next's default unstyled crash screen. Keeps the warm-glass
 * identity and offers a retry that re-runs the failed segment.
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-4 pb-20 pt-24 text-center">
      <div className="glass max-w-md rounded-3xl px-8 py-12">
        <FileWarning className="mx-auto h-8 w-8 text-muted-foreground" />
        <h1 className="mt-4 font-display text-3xl font-bold tracking-tight">
          The archive hit a snag
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Something failed while laying out this page. The filings are safe on
          the shelf — try again, or head back to the archive.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <button
            type="button"
            onClick={reset}
            className="inline-flex h-9 items-center rounded-full bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex h-9 items-center rounded-full border border-border px-4 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Back to the archive
          </Link>
        </div>
        {error.digest && (
          <p className="mt-6 font-mono text-[10px] text-muted-foreground/70">
            reference {error.digest}
          </p>
        )}
        <p className="mt-4 font-mono text-[10px] text-muted-foreground">
          Even the best cataloguers drop a card sometimes. — The Curator
        </p>
      </div>
    </main>
  );
}
