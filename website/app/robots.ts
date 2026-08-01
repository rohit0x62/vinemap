import type { MetadataRoute } from "next";
import { LINKS } from "./links";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${LINKS.site}/sitemap.xml`,
  };
}
