import { FAQS } from "./faqs";
import { LINKS, VERSION } from "./links";

export function JsonLd() {
  const software = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Vinemap",
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Windows, macOS, Linux",
    description:
      "Local-first code graph and MCP context engine for AI coding agents. Delivers token-budgeted context to Cursor, Claude Code, and Codex CLI.",
    url: LINKS.site,
    downloadUrl: LINKS.pypi,
    softwareVersion: VERSION,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: "Free tier up to 500 files",
    },
    author: {
      "@type": "Organization",
      name: "WINK",
      url: LINKS.github,
    },
  };

  const organization = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "WINK",
    url: LINKS.github,
    sameAs: [LINKS.github, LINKS.pypi],
  };

  const faqPage = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQS.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };

  const website = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Vinemap",
    url: LINKS.site,
    description:
      "Graph-native context for AI coding agents — local code graph, MCP server, token-budgeted packs.",
    publisher: {
      "@type": "Organization",
      name: "WINK",
    },
  };

  const blocks = [software, organization, faqPage, website];

  return (
    <>
      {blocks.map((block) => (
        <script
          key={block["@type"]}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(block) }}
        />
      ))}
    </>
  );
}
