"use client";

import * as React from "react";
import dynamic from "next/dynamic";

// `ssr: false` is only allowed inside a Client Component, so the dynamic
// import lives here and layout.tsx (a Server Component) renders this wrapper.
// Keeps the Lenis library off the critical hydration path.
const LenisProvider = dynamic(
  () => import("@/components/lenis-provider").then((m) => m.LenisProvider),
  { ssr: false },
);

export default function LenisWrapper({ children }: { children: React.ReactNode }) {
  return <LenisProvider>{children}</LenisProvider>;
}
