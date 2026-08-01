import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { LINKS, VERSION } from "./links";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600", "700"],
});

const title = "Vinemap — Graph-native context for AI coding agents";
const description =
  "Vinemap builds a local code graph of your repo and pre-loads token-budgeted context into Claude Code, Cursor, Codex CLI, and any MCP agent. 100% local, zero dependencies.";

export const metadata: Metadata = {
  metadataBase: new URL(LINKS.site),
  title,
  description,
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
  ],
  authors: [{ name: "WINK", url: LINKS.github }],
  openGraph: {
    type: "website",
    url: LINKS.site,
    title,
    description,
    siteName: "Vinemap",
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
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
      <body className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
