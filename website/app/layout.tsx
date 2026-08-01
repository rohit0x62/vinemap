import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { JsonLd } from "./json-ld";
import { LINKS, VERSION } from "./links";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const title = "Vinemap — Graph-native context for AI coding agents";
const description =
  "Vinemap builds a local code graph of your repo and pre-loads token-budgeted context into Claude Code, Cursor, Codex CLI, and any MCP agent. 100% local, zero dependencies.";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#5865f2",
};

export const metadata: Metadata = {
  metadataBase: new URL(LINKS.site),
  title: {
    default: title,
    template: "%s · Vinemap",
  },
  description,
  applicationName: "Vinemap",
  keywords: [
    "Vinemap",
    "AI coding agent",
    "MCP",
    "Model Context Protocol",
    "code graph",
    "Cursor",
    "Claude Code",
    "Codex CLI",
    "context engine",
    "local RAG alternative",
    "token optimization",
    "developer tools",
  ],
  authors: [{ name: "WINK", url: LINKS.github }],
  creator: "WINK",
  publisher: "WINK",
  category: "technology",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
    },
  },
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    type: "website",
    url: LINKS.site,
    title,
    description,
    siteName: "Vinemap",
    locale: "en_US",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Vinemap — graph-native context for AI coding agents",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: ["/og-image.png"],
  },
  alternates: {
    canonical: LINKS.site,
  },
  other: {
    "pypi:version": VERSION,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://pypi.org" />
        <link rel="dns-prefetch" href="https://github.com" />
      </head>
      <body className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
        <JsonLd />
        {children}
      </body>
    </html>
  );
}
