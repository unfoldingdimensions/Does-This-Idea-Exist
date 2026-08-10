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

const nextConfig: NextConfig = {
  poweredByHeader: false,
  headers: securityHeaders,
};

export default nextConfig;
