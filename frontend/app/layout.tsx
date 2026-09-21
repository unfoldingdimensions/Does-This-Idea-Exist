import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Space_Grotesk, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { SkyStage } from "@/components/sky-stage";
import LenisWrapper from "@/components/lenis-wrapper";
import { siteUrl } from "@/lib/site";
import "./globals.css";
import { cn } from "@/lib/utils";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "IdeaExists — Does this startup exist?",
  description:
    "A human-kept archive of what exists — searchable startups with their websites and code. Verified locally, refreshed weekly, nothing tracked.",
  // NOTE: no `alternates.canonical` here. The root layout is inherited by
  // every route including /products/<slug>, and a canonical of "/" told
  // crawlers each product page was a duplicate of the home page. Product
  // pages now export their own metadata (see products/[slug]/page.tsx's
  // sibling metadata file) and self-canonicalise; pages without their own
  // canonical simply fall back to the URL's canonical form.
  openGraph: {
    type: "website",
    siteName: "IdeaExists",
    title: "IdeaExists — Does this startup exist?",
    description:
      "A human-kept archive of what exists — searchable startups with their websites and code. Verified locally, refreshed weekly, nothing tracked.",
    // Site-level OG default (no url: "/" — same reasoning as the canonical
    // removal above; per-page OG would override it).
    locale: "en_US",
  },
  twitter: {
    card: "summary",
    title: "IdeaExists — Does this startup exist?",
    description:
      "A human-kept archive of what exists — searchable startups with their websites and code. Verified locally, refreshed weekly, nothing tracked.",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "h-full",
        "antialiased",
        jakarta.variable,
        spaceGrotesk.variable,
        geistMono.variable,
        "font-sans",
      )}
    >
      <body className="min-h-full flex flex-col bg-background font-sans">
        <SkyStage />
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <LenisWrapper>{children}</LenisWrapper>
          <Toaster position="top-center" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
