"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="copy-btn"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        });
      }}
    >
      {copied ? "copied" : "copy"}
    </button>
  );
}

const OS_TABS = [
  {
    id: "unix",
    label: "macOS / Linux",
    lang: "bash",
    copy: "pip install vinemap",
    lines: [
      { c: "comment", t: "# one install — pure Python, zero dependencies" },
      { c: "cmd", t: "$ pip install vinemap" },
    ],
  },
  {
    id: "windows",
    label: "Windows",
    lang: "powershell",
    copy: "pip install vinemap",
    lines: [
      { c: "comment", t: "# PowerShell — Python 3.9+ from python.org or the py launcher" },
      { c: "cmd", t: "> pip install vinemap" },
    ],
  },
];

export function InstallTabs() {
  const [active, setActive] = useState(OS_TABS[0].id);
  const tab = OS_TABS.find((t) => t.id === active) ?? OS_TABS[0];
  return (
    <div className="term">
      <div className="term-head">
        <div className="tabs">
          {OS_TABS.map((t) => (
            <button
              key={t.id}
              className={t.id === active ? "tab on" : "tab"}
              onClick={() => setActive(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="term-actions">
          <span className="term-lang">{tab.lang}</span>
          <CopyButton text={tab.copy} />
        </div>
      </div>
      <pre>
        {tab.lines.map((l, i) => (
          <span key={i} className={`ln-${l.c}`}>
            {l.t}
            {"\n"}
          </span>
        ))}
      </pre>
    </div>
  );
}

const RETRIEVAL_CYCLE = [
  {
    query: "graph_retrieve('auth flow')",
    hits: ["auth.ts", "middleware", "api/"],
    tokens: 842,
    ms: 41,
  },
  {
    query: "graph_retrieve('db pool')",
    hits: ["db.py", "config", "utils"],
    tokens: 612,
    ms: 38,
  },
  {
    query: "graph_retrieve('api tests')",
    hits: ["tests/", "api/", "fixtures"],
    tokens: 534,
    ms: 35,
  },
] as const;

export function ContextGraphViz() {
  const [cycleIdx, setCycleIdx] = useState(0);
  const [hudPhase, setHudPhase] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    setReducedMotion(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  useEffect(() => {
    if (reducedMotion) {
      setHudPhase(3);
      return;
    }
    const interval = window.setInterval(() => {
      setCycleIdx((i) => (i + 1) % RETRIEVAL_CYCLE.length);
      setHudPhase(0);
    }, 4200);
    return () => window.clearInterval(interval);
  }, [reducedMotion]);

  useEffect(() => {
    if (reducedMotion) return;
    const interval = window.setInterval(() => {
      setHudPhase((p) => (p < 3 ? p + 1 : p));
    }, 700);
    return () => window.clearInterval(interval);
  }, [cycleIdx, reducedMotion]);

  const cycle = RETRIEVAL_CYCLE[cycleIdx % RETRIEVAL_CYCLE.length];

  return (
    <div className="live-retrieval" aria-label="Live graph retrieval demo">
      <div className="live-retrieval-chrome">
        <span className="live-retrieval-dot" />
        <span className="live-retrieval-dot" />
        <span className="live-retrieval-dot" />
        <span className="live-retrieval-title">vinemap — mcp</span>
      </div>

      <div className="graph-hud">
        <div className="graph-hud-head">
          <span className="graph-hud-live">Live retrieval</span>
          <span className="graph-hud-ms">{cycle.ms}ms</span>
        </div>
        <div className={`graph-hud-line graph-hud-query${hudPhase >= 0 ? " on" : ""}`}>
          <span className="graph-hud-prompt">$</span> {cycle.query}
        </div>
        <div className={`graph-hud-line graph-hud-hit${hudPhase >= 1 ? " on" : ""}`}>
          <span className="graph-hud-arrow">→</span>
          <span className="graph-hud-files">
            {cycle.hits.map((hit) => (
              <span className="graph-hud-file" key={hit}>{hit}</span>
            ))}
          </span>
        </div>
        <div className={`graph-hud-line graph-hud-pack${hudPhase >= 2 ? " on" : ""}`}>
          pack: <strong>{cycle.tokens}</strong> tokens · injected to agent
        </div>
        <div className="graph-hud-bar">
          <span style={{ width: hudPhase >= 2 ? "100%" : hudPhase >= 1 ? "62%" : "28%" }} />
        </div>
      </div>
    </div>
  );
}

const MATRIX_COLUMNS = [
  { key: "graph", label: "Structural graph", short: "Graph" },
  { key: "local", label: "100% local", short: "Local" },
  { key: "memory", label: "Session memory", short: "Memory" },
  { key: "inject", label: "Pre-injection", short: "Inject" },
] as const;

export function FeatureMatrix({
  rows,
}: {
  rows: {
    tool: string;
    sub: string;
    self?: boolean;
    cells: boolean[];
  }[];
}) {
  return (
    <div className="feature-matrix">
      <div className="feature-matrix-head">
        <div className="feature-matrix-title">
          <span className="feature-matrix-kicker">Feature matrix</span>
          <strong>Vinemap leads on every axis</strong>
        </div>
        <div className="feature-matrix-legend">
          <span><i className="legend-yes" /> Supported</span>
          <span><i className="legend-no" /> Missing</span>
        </div>
      </div>

      <div className="feature-matrix-grid">
        <div className="matrix-header-row">
          <div className="matrix-corner">Approach</div>
          {MATRIX_COLUMNS.map((col) => (
            <div className="matrix-col-head" key={col.key}>
              <span className="matrix-col-short">{col.short}</span>
              <span className="matrix-col-label">{col.label}</span>
            </div>
          ))}
          <div className="matrix-col-head matrix-score-head">Score</div>
        </div>

        {rows.map((row, rowIdx) => {
          const score = row.cells.filter(Boolean).length;
          return (
            <div
              className={`matrix-row${row.self ? " matrix-row-self" : ""}`}
              key={row.tool}
              style={{ animationDelay: `${rowIdx * 0.07}s` }}
            >
              <div className="matrix-row-label">
                <strong>{row.tool}</strong>
                <span>{row.sub}</span>
                {row.self ? <em className="matrix-badge">Best fit</em> : null}
              </div>
              {row.cells.map((on, i) => (
                <div className={`matrix-cell${on ? " matrix-cell-yes" : " matrix-cell-no"}`} key={i}>
                  <span className="matrix-cell-inner">
                    {on ? (
                      <svg viewBox="0 0 16 16" aria-hidden="true">
                        <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
                      </svg>
                    ) : (
                      "—"
                    )}
                  </span>
                  <span className="matrix-cell-fill" style={{ opacity: on ? 1 : 0 }} />
                </div>
              ))}
              <div className="matrix-score">
                <span className="matrix-score-num">{score}/4</span>
                <span className="matrix-score-bar">
                  <i style={{ width: `${(score / 4) * 100}%` }} />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Reveal({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={`reveal${visible ? " is-visible" : ""}${className ? ` ${className}` : ""}`}>
      {children}
    </div>
  );
}
