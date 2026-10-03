"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { AdminConsole, isAdminSection, type AdminSection } from "@/components/admin-console";

/**
 * `/admin?section=usage` — the owner console as a real page.
 *
 * The URL is the state, so a section is bookmarkable, the back button steps
 * through the sections you visited, and a link can point straight at one. The
 * console itself is router-free (it takes the section as a prop); this file is
 * the only place that knows about the query string.
 *
 * An unknown or absent `?section=` falls back to Seeding rather than blanking the
 * page — a stale bookmark should land somewhere useful, not on nothing.
 */
function AdminRoute() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("section");
  const section: AdminSection = isAdminSection(requested) ? requested : "seed";

  const onSectionChange = React.useCallback(
    (next: AdminSection) => {
      // `replace`, not `push`: stepping through six sections should not bury the
      // archive six entries deep in the back button.
      router.replace(next === "seed" ? "/admin" : `/admin?section=${next}`, { scroll: false });
    },
    [router],
  );

  return <AdminConsole section={section} onSectionChange={onSectionChange} />;
}

export default function AdminPage() {
  // useSearchParams needs a Suspense boundary above it (Next prerenders this
  // route's shell), and a console with no section is not a state worth showing.
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      }
    >
      <AdminRoute />
    </Suspense>
  );
}
