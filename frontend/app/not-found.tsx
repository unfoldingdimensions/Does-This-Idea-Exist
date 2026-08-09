import Link from "next/link";
import { Archive } from "lucide-react";

/**
 * Themed 404 — the archive's dead-end in its own voice (review finding #5).
 * Stock Next 404 had no branding and no way home; this keeps the warm-glass
 * identity and offers a single, obvious path back to the archive.
 */
export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-4 pb-20 pt-24 text-center">
      <div className="glass max-w-md rounded-3xl px-8 py-12">
        <Archive className="mx-auto h-8 w-8 text-muted-foreground" />
        <h1 className="mt-4 font-display text-3xl font-bold tracking-tight">404</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Nothing in the archive matches — not even this page. It was never filed, or it&rsquo;s
          been shelved somewhere the stacks don&rsquo;t reach.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex h-9 items-center gap-1.5 rounded-full bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Back to the archive
        </Link>
        <p className="mt-6 font-mono text-[10px] text-muted-foreground">
          Dead links, unlike dead startups, are recoverable. — The Curator
        </p>
      </div>
    </main>
  );
}
