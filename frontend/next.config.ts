import path from "node:path";
import type { NextConfig } from "next";

// Security headers (M3 fix, additive):
// - Always: nosniff, frame-deny, no-referrer, permissions policy.
// - Production: strict CSP. It ships `script-src 'self' 'unsafe-inline'`
//   because Next 16 inlines the RSC bootstrap script in the HTML — a nonce or
//   hash-based strict policy is the hosting-time upgrade. connect-src must
//   match NEXT_PUBLIC_API_BASE (default localhost:8020) or the app breaks.
// - Dev keeps working without CSP (Next dev injects inline scripts/styles).
const securityHeaders = (): Array<{ source: string; headers: Array<{ key: string; value: string }> }> => {
  const isProd = process.env.NODE_ENV === "production";
  const apiOrigin = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8020";
  const headers = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Referrer-Policy", value: "no-referrer" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), browsing-topics=()" },
  ];
  if (isProd) {
    // HSTS belongs on the frontend host too, not just the API (which sets its
    // own in app/main.py): without it a first-visit downgrade can strip TLS
    // before the app loads. Browsers ignore it over http/localhost, so the
    // local prod-build path (ALLOW_LOCALHOST_BUILD) is unaffected.
    headers.push({
      key: "Strict-Transport-Security",
      value: "max-age=63072000; includeSubDomains",
    });
    headers.push({
      key: "Content-Security-Policy",
      value: [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        `connect-src 'self' ${apiOrigin}`,
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
      ].join("; "),
    });
  }
  return [{ source: "/(.*)", headers }];
};

// NEXT_PUBLIC_* vars are inlined at build time. A production build without
// them silently ships a frontend that fetches localhost:8020 and stamps
// localhost:3023 into canonicals/OG/sitemap — wrecking the app and SEO with
// no error anywhere. Fail the build loudly instead. Set ALLOW_LOCALHOST_BUILD=1
// to intentionally cut a local prod build for testing.
const assertProdEnv = (): void => {
  if (process.env.NODE_ENV !== "production" || process.env.ALLOW_LOCALHOST_BUILD === "1") return;
  const offenders: string[] = [];
  const api = process.env.NEXT_PUBLIC_API_BASE;
  const site = process.env.NEXT_PUBLIC_SITE_URL;
  // new URL throws on a scheme-less value ("api.example.com"), which would
  // surface as an opaque TypeError instead of the curated message below —
  // so parse defensively and treat an unparseable value as an offender too.
  const host = (v: string | undefined): string | null => {
    if (!v) return null;
    try {
      return new URL(v).hostname;
    } catch {
      return "localhost"; // unparseable → fail the build like localhost does
    }
  };
  if (!api || host(api) === "localhost") offenders.push("NEXT_PUBLIC_API_BASE");
  if (!site || host(site) === "localhost") offenders.push("NEXT_PUBLIC_SITE_URL");
  if (offenders.length > 0) {
    throw new Error(
      `Refusing production build: ${offenders.join(", ")} unset, malformed, or pointing at localhost. ` +
        "These are inlined at build time — a build without them ships a broken app. " +
        "Set them to the deployed origins with a scheme (see DEPLOYMENT.md), or set " +
        "ALLOW_LOCALHOST_BUILD=1 to override for local testing.",
    );
  }
};
assertProdEnv();

const nextConfig: NextConfig = {
  poweredByHeader: false,
  headers: securityHeaders,
  // The repo root has a wrapper package-lock.json (test runner only); without
  // this Next guesses the wrong workspace root and warns about multiple
  // lockfiles on every dev/build. The app's tracing root is the frontend dir.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
