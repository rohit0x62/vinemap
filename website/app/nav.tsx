"use client";

import { useEffect, useState } from "react";
import { GitHubIcon, Logo } from "./logo";
import { LINKS } from "./links";

const NAV_ITEMS: Array<
  { href: string; label: string; external?: boolean }
> = [
  { href: "#install", label: "Install" },
  { href: "#hood", label: "How it works" },
  { href: "#compare", label: "Compare" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: LINKS.pypi, label: "PyPI", external: true },
];

export function SiteNav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <nav className="nav animate-nav" aria-label="Primary">
      <div className="container nav-inner">
        <a className="brand" href={LINKS.site}>
          <Logo />
          Vinemap
        </a>

        <button
          type="button"
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="nav-toggle-bar" />
          <span className="nav-toggle-bar" />
          <span className="nav-toggle-bar" />
        </button>

        <div className={`nav-links${open ? " nav-links-open" : ""}`} id="mobile-menu">
          <div className="nav-links-scroll">
            {NAV_ITEMS.map((item) =>
              item.external ? (
                <a
                  key={item.href}
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={close}
                >
                  {item.label}
                </a>
              ) : (
                <a key={item.href} href={item.href} onClick={close}>
                  {item.label}
                </a>
              ),
            )}
            <a
              className="btn btn-white nav-btn-github"
              href={LINKS.github}
              target="_blank"
              rel="noopener noreferrer"
              onClick={close}
            >
              <GitHubIcon />
              GitHub
            </a>
            <a className="btn btn-green nav-btn-install" href="#install" onClick={close}>
              Install Free
            </a>
          </div>
        </div>

        {open ? (
          <button
            type="button"
            className="nav-backdrop"
            aria-label="Close menu"
            onClick={close}
          />
        ) : null}
      </div>
    </nav>
  );
}
