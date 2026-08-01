import { ContextGraphViz, CopyButton, FeatureMatrix, InstallTabs, Reveal } from "./components";
import { LINKS, VERSION } from "./links";

const EDITORS = ["VS Code", "JetBrains", "Neovim", "Sublime", "Zed", "Terminal"];

const LANGS = [
  "Python", "TypeScript", "JavaScript", "Go", "Java", "Rust",
  "C / C++", "C#", "Ruby", "PHP", "Kotlin", "Swift",
];

const COMPARISON = [
  { tool: "Vinemap", sub: "graph + pre-injection", self: true, cells: [true, true, true, true] },
  { tool: "Repo dumps", sub: "Repomix", self: false, cells: [false, true, false, false] },
  { tool: "Repo maps", sub: "Aider", self: false, cells: [true, true, false, false] },
  { tool: "Embedding RAG", sub: "Continue.dev", self: false, cells: [false, true, false, false] },
  { tool: "Cloud context engines", sub: "Augment · Greptile · Cody", self: false, cells: [true, false, true, false] },
];

const INSTALL_STATS = [
  { value: "<60s", label: "Setup time" },
  { value: "2", label: "Commands" },
  { value: "0", label: "Accounts needed" },
];

const COMPARE_FEATURES = [
  { key: "graph", label: "Structural graph", hint: "Knows imports, calls, and edges" },
  { key: "local", label: "100% local", hint: "Code never leaves your machine" },
  { key: "memory", label: "Session memory", hint: "Remembers what you touched last turn" },
  { key: "inject", label: "Pre-injection", hint: "Context packed before the agent reads" },
];

const APPROACH_PITFALLS = [
  {
    name: "Repo dump",
    tag: "Repomix-style",
    flaw: "Token firehose",
    detail: "Ships entire files — most of it irrelevant noise.",
  },
  {
    name: "Repo map",
    tag: "Aider-style",
    flaw: "Static snapshot",
    detail: "Shows structure but no live session recall.",
  },
  {
    name: "Embedding RAG",
    tag: "Similarity search",
    flaw: "Guesswork retrieval",
    detail: "Finds lookalikes, not the actual call chain.",
  },
  {
    name: "Cloud engine",
    tag: "Remote index",
    flaw: "Off-device",
    detail: "Your codebase indexed on someone else's servers.",
  },
];

const FAQS = [
  {
    q: "Does my code leave my machine?",
    a: "No. The graph, session memory, and context packs are stored in .vinemap/ inside your project. The MCP server runs locally over stdio — no code, no file names, no project data is ever sent externally.",
  },
  {
    q: "Which AI tools does Vinemap work with?",
    a: "Claude Code, Codex CLI, Cursor, Gemini CLI, GitHub Copilot, OpenCode, and any other MCP-compatible agent. The same install works across all of them.",
  },
  {
    q: "Do I need to run something every session?",
    a: "No. Run `vinemap index .` once, then `vinemap connect <agent>` — after that your agent talks to the local server automatically, and the graph re-syncs incrementally as files change.",
  },
  {
    q: "What happens when my files change?",
    a: "Only touched files are re-parsed thanks to content-hash caching, so updates are sub-second on most projects. No manual rebuilds.",
  },
  {
    q: "What do I get in Pro?",
    a: "Up to 1M files per project, crash diagnosis with blast-radius analysis, decision & WHY memory across sessions, coverage confidence scores, and codebase-health tools (circular deps, dead exports). $10/month, cancel anytime.",
  },
  {
    q: "How does Teams work?",
    a: "Teams adds a shared graph across your organization's repos with per-developer views and shared decision memory — self-hosted or in your VPC, priced per seat.",
  },
];

const RUN_CMD = "vinemap index . && vinemap connect cursor";

/* simple tile glyphs (16px stroke icons) */
function Glyph({ kind }: { kind: string }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (kind) {
    case "burst":
      return (
        <svg {...common}>
          <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
        </svg>
      );
    case "gear":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3.4" />
          <path d="M12 2.8v3M12 18.2v3M2.8 12h3M18.2 12h3M5.2 5.2l2.1 2.1M16.7 16.7l2.1 2.1M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1" />
        </svg>
      );
    case "cube":
      return (
        <svg {...common}>
          <path d="M12 3 4.5 7v10L12 21l7.5-4V7L12 3Z" />
          <path d="M4.5 7 12 11l7.5-4M12 11v10" />
        </svg>
      );
    case "spark":
      return (
        <svg {...common}>
          <path d="M12 3c.6 4.8 4.2 8.4 9 9-4.8.6-8.4 4.2-9 9-.6-4.8-4.2-8.4-9-9 4.8-.6 8.4-4.2 9-9Z" />
        </svg>
      );
    case "bot":
      return (
        <svg {...common}>
          <rect x="5" y="8" width="14" height="11" rx="3" />
          <path d="M12 8V4.5M9.5 13h.01M14.5 13h.01" />
        </svg>
      );
    case "term":
      return (
        <svg {...common}>
          <rect x="3.5" y="5" width="17" height="14" rx="2.5" />
          <path d="m7 10 3 2.5L7 15M12.5 15H17" />
        </svg>
      );
    case "peak":
      return (
        <svg {...common}>
          <path d="M4 19 12 5l8 14M8.5 13.5h7" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" />
        </svg>
      );
  }
}

const AGENT_TILES: { name: string; glyph: string }[] = [
  { name: "Claude", glyph: "burst" },
  { name: "Codex", glyph: "gear" },
  { name: "Cursor", glyph: "cube" },
  { name: "Gemini", glyph: "spark" },
  { name: "Copilot", glyph: "bot" },
  { name: "OpenCode", glyph: "term" },
  { name: "Antigravity", glyph: "peak" },
];

function Logo({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M6 26V13c0-4 3-7 7-7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M26 26V13c0-4-3-7-7-7" stroke="#5865f2" strokeWidth="3" strokeLinecap="round" />
      <circle cx="16" cy="6" r="3" fill="currentColor" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

export default function Home() {
  return (
    <>
      <nav className="nav animate-nav">
        <div className="container nav-inner">
          <a className="brand" href={LINKS.site}>
            <Logo />
            Vinemap
          </a>
          <div className="nav-links">
            <a href="#install">Install</a>
            <a href="#hood">How it works</a>
            <a href="#compare">Compare</a>
            <a href="#pricing">Pricing</a>
            <a href="#faq">FAQ</a>
            <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">PyPI</a>
            <a className="btn btn-white" href={LINKS.github} target="_blank" rel="noopener noreferrer">
              <GitHubIcon />
              GitHub
            </a>
            <a className="btn btn-green" href="#install">Install Free</a>
          </div>
        </div>
      </nav>

      <header className="hero-zone">
        <div className="container">
          <div className="announce-pill animate-hero-pill">
            <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">
              <span>
                <i className="dot" />
                v{VERSION} on PyPI · works with Codex · Claude Code · Cursor · Copilot
                <em>→</em>
              </span>
            </a>
          </div>

          <div className="hero-card animate-hero-card">
            <div className="hero-layout">
              <div className="hero-copy">
                <h1 className="animate-hero-title">
                  <mark>Graph-native context</mark> for AI coding agents
                </h1>
                <p className="hero-sub animate-hero-sub">
                  Map your repo once. Vinemap injects the exact files your agent needs —{" "}
                  <b>before the first tool call</b>, 100% on your machine.
                </p>
                <div className="hero-chips animate-hero-chips">
                  <span className="chip">[MCP]</span>
                  <span className="chip">[GRAPH]</span>
                  <span className="chip">[LOCAL]</span>
                </div>
                <div className="hero-ctas animate-hero-ctas">
                  <a className="btn btn-green" href="#install">Install Free →</a>
                  <a className="btn btn-white" href={LINKS.github} target="_blank" rel="noopener noreferrer">
                    <GitHubIcon />
                    View on GitHub
                    <span className="count">v{VERSION}</span>
                  </a>
                </div>
                <p className="hero-note animate-hero-note">
                  100% local — nothing leaves your machine · free up to 500 files · no account, no API keys
                </p>
              </div>
              <ContextGraphViz />
            </div>
          </div>
        </div>
      </header>

      <section className="agents-zone">
        <div className="container">
          <p className="mono-label animate-agents-label">MCP ready for</p>
          <div className="tiles">
            {AGENT_TILES.map((a) => (
              <a className="tile" href="#install" key={a.name}>
                <span className="box">
                  <Glyph kind={a.glyph} />
                </span>
                <span className="name">{a.name}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <Reveal>
      <section className="section install-section" id="install">
        <div className="container">
          <div className="install-header center">
            <span className="kicker">Get started</span>
            <h2 className="h2">Install in under a minute.</h2>
            <p className="lede">
              One global install via{" "}
              <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">PyPI</a>
              {" "}or our{" "}
              <a href={LINKS.github} target="_blank" rel="noopener noreferrer">GitHub</a>
              {" "}installers, then run on any project. <b>Python 3.9+</b> is the only requirement.
            </p>
            <div className="install-stats">
              {INSTALL_STATS.map((stat) => (
                <div className="install-stat" key={stat.label}>
                  <strong>{stat.value}</strong>
                  <span>{stat.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="install-timeline">
            <div className="install-step-card">
              <div className="step-block">
                <div className="step-num">1</div>
                <div className="step-body">
                  <div className="step-meta">
                    <span className="step-tag">Global install</span>
                    <span className="step-time">~15 sec</span>
                  </div>
                  <h3>Install once</h3>
                  <p>Pure Python, zero dependencies — works offline, never breaks on a transitive pin.</p>
                  <InstallTabs />
                </div>
              </div>
            </div>

            <div className="install-step-card">
              <div className="step-block">
                <div className="step-num">2</div>
                <div className="step-body">
                  <div className="step-meta">
                    <span className="step-tag">Per project</span>
                    <span className="step-time">~45 sec</span>
                  </div>
                  <h3>Run in your project</h3>
                  <p>
                    Run <code>vinemap index .</code> in your project directory to build the graph,
                    then <code>vinemap connect cursor</code> (or <code>claude</code>,{" "}
                    <code>gemini</code>, <code>codex</code>) to wire up your AI tool automatically.
                  </p>
                  <div className="term">
                    <div className="term-head">
                      <div className="tabs">
                        <span className="tab on">terminal</span>
                      </div>
                      <div className="term-actions">
                        <CopyButton text={RUN_CMD} />
                      </div>
                    </div>
                    <pre>
                      <span className="ln-cmd">$ vinemap index .{"\n"}</span>
                      <span className="ln-ok">indexed 1,204 files — 8,913 symbols, 3,412 import edges in 1.9s{"\n"}</span>
                      <span className="ln-cmd">$ vinemap connect cursor{"\n"}</span>
                      <span className="ln-violet">wrote .cursor/mcp.json{"\n"}</span>
                      <span className="ln-ok">✓ graph tools live — graph_retrieve · graph_read · graph_neighbors{"\n"}</span>
                      <span className="ln-prompt">→ reload your agent and ask away</span>
                    </pre>
                  </div>
                  <div className="agent-chips">
                    {AGENT_TILES.map((a) => (
                      <span className="chip" key={a.name}>{a.name}</span>
                    ))}
                  </div>
                  <div>
                    <span className="local-note">🔒 100% local — nothing leaves your machine.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="install-editors">
            <div className="center">
              <h2 className="h2 install-editors-title">Works inside any editor</h2>
              <p className="lede">MCP runs over stdio — no plugin required.</p>
            </div>
            <div className="editors">
              {EDITORS.map((e) => (
                <span key={e}>{e}</span>
              ))}
            </div>
            <p className="editors-note">
              …and any other editor with a terminal — Emacs, Helix, Fleet, you name it.
            </p>
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <section className="section" id="hood" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="center">
            <span className="kicker">Under the hood</span>
            <h2 className="h2">A dual graph of your project.</h2>
            <p className="lede">
              Vinemap builds two layers — a structural map of your code and a live memory of
              your session — and uses both to deliver precise context.
            </p>
          </div>
          <div className="trio">
            <div className="trio-card">
              <span className="tag">Code Map</span>
              <h3>Your project&rsquo;s DNA</h3>
              <p>
                A complete graph of your codebase — every file, function, and class, and how
                they connect. Built in seconds, updated incrementally.
              </p>
              <ul>
                <li>Files, functions, classes with line ranges</li>
                <li>Import and dependency edges between files</li>
                <li>Call-edge and keyword scoring for ranking</li>
              </ul>
            </div>
            <div className="trio-card">
              <span className="tag">Context Packer</span>
              <h3>The intelligence layer</h3>
              <p>
                Compresses graph results into a compact structured summary — not raw file
                dumps. Your agent gets more understanding in fewer tokens.
              </p>
              <ul>
                <li>Full signatures with params and returns</li>
                <li>Inline code from the most relevant functions</li>
                <li>Hard token budgets — the pack always fits</li>
              </ul>
            </div>
            <div className="trio-card">
              <span className="tag">Session Memory</span>
              <h3>Smarter every turn</h3>
              <p>
                Tracks what has been read, edited, and decided. Follow-up questions route
                straight to previously relevant files.
              </p>
              <ul>
                <li>Touched files weighted higher next turn</li>
                <li>Decisions carry across sessions</li>
                <li>No cold starts on your own codebase</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="center">
            <span className="kicker">The exploration tax</span>
            <h2 className="h2">
              Stop paying for <mark>blind search</mark>.
            </h2>
          </div>
          <div className="vs">
            <div className="vs-col bad">
              <h3>Without Vinemap</h3>
              <ol>
                <li>You ask a question</li>
                <li>Agent calls grep, Bash, Read</li>
                <li>Reads 10–20 files to find context</li>
                <li>More exploration, more tool calls…</li>
                <li>Finally answers your question</li>
              </ol>
              <p className="verdict">Thousands of tokens wasted on exploration, every turn.</p>
            </div>
            <div className="vs-col good">
              <h3>With Vinemap</h3>
              <ol>
                <li>You ask a question</li>
                <li>The graph packs the correct context instantly</li>
                <li>Agent answers with full context</li>
              </ol>
              <p className="verdict">One pass. Zero exploration overhead. Better answers.</p>
            </div>
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <section className="section compare-section" id="compare" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="compare-header center">
            <span className="kicker">Compare</span>
            <h2 className="h2">Why a graph beats a dump, a map, or a cloud.</h2>
            <p className="lede">
              Repo dumps send everything. Embedding RAG guesses by similarity. Cloud engines
              need your code on their servers. Vinemap routes <b>exact structural context</b> locally.
            </p>
          </div>

          <div className="compare-features">
            {COMPARE_FEATURES.map((feature) => (
              <div className="compare-feature" key={feature.key}>
                <span className="compare-feature-label">{feature.label}</span>
                <span className="compare-feature-hint">{feature.hint}</span>
              </div>
            ))}
          </div>

          <div className="approach-grid">
            {APPROACH_PITFALLS.map((approach) => (
              <div className="approach-card" key={approach.name}>
                <span className="approach-tag">{approach.tag}</span>
                <h3>{approach.name}</h3>
                <p className="approach-flaw">{approach.flaw}</p>
                <p>{approach.detail}</p>
              </div>
            ))}
            <div className="approach-card approach-card-win">
              <span className="approach-tag">Vinemap</span>
              <h3>Graph + pre-injection</h3>
              <p className="approach-flaw">All four dimensions</p>
              <p>Structural graph, session memory, and packed context — 100% on your machine.</p>
            </div>
          </div>

          <FeatureMatrix rows={COMPARISON} />
          <div className="agent-chips compare-langs">
            {LANGS.map((l) => (
              <span className="chip" key={l}>{l}</span>
            ))}
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <section className="section" id="pricing" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="center">
            <span className="kicker">Pricing</span>
            <h2 className="h2">Start free. Scale when you need it.</h2>
          </div>
          <div className="pricing">
            <div className="plan">
              <div className="name">Standard</div>
              <div className="price">Free</div>
              <p className="blurb">Up to 500 files · forever</p>
              <ul>
                <li>Graph-first context</li>
                <li>Works with any AI tool</li>
                <li>Zero configuration</li>
                <li>Session memory</li>
                <li>100% local &amp; private</li>
              </ul>
              <a className="btn btn-white" href="#install">Get started — free</a>
            </div>
            <div className="plan featured">
              <span className="flag">7-day free trial</span>
              <div className="name">Pro</div>
              <div className="price">$10<small>/mo</small></div>
              <p className="blurb">$0 for 7 days · cancel anytime · up to 1M files</p>
              <ul>
                <li>Everything in Standard</li>
                <li>Instant crash diagnosis with blast radius</li>
                <li>Decision &amp; WHY memory</li>
                <li>Coverage confidence score</li>
                <li>Circular deps &amp; dead export detection</li>
                <li>Exhaustive audit mode</li>
              </ul>
              <a className="btn btn-green" href="#install">Start free trial</a>
            </div>
            <div className="plan">
              <div className="name">Teams</div>
              <div className="price">Custom</div>
              <p className="blurb">Large teams &amp; orgs · self-hosted or VPC</p>
              <ul>
                <li>Everything in Pro</li>
                <li>Shared team graph</li>
                <li>Per-developer views</li>
                <li>Priority onboarding</li>
                <li>Direct support</li>
              </ul>
              <a className="btn btn-white" href={LINKS.contact}>Talk to us</a>
            </div>
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="duo">
            <div className="duo-card">
              <span className="live"><i />LIVE NOW</span>
              <h3>Join the Vinemap community</h3>
              <p>
                Connect with other developers on{" "}
                <a href={LINKS.community} target="_blank" rel="noopener noreferrer">GitHub Discussions</a>
                , share your setup, and get help configuring Vinemap for your codebase.
              </p>
              <a className="btn btn-discord" href={LINKS.community} target="_blank" rel="noopener noreferrer">GitHub Discussions</a>
            </div>
            <div className="duo-card">
              <span className="live"><i />REAL FEEDBACK</span>
              <h3>Got feedback or ideas?</h3>
              <p>
                We read every message. Open a{" "}
                <a href={LINKS.githubIssues} target="_blank" rel="noopener noreferrer">GitHub issue</a>
                {" "}or email us — custom plans, larger codebases, or setup help.
              </p>
              <a className="btn btn-white" href={LINKS.githubIssues} target="_blank" rel="noopener noreferrer">Open an issue</a>
            </div>
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <section className="section" id="faq" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="center">
            <span className="kicker">FAQ</span>
            <h2 className="h2">Frequently asked questions</h2>
          </div>
          <div className="faq">
            {FAQS.map((f) => (
              <details key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
      </Reveal>

      <Reveal>
      <div className="cta">
        <div className="container">
          <div className="cta-card">
            <h2>
              Give your codebase <mark>a brain</mark>.
            </h2>
            <p>One global install, then run on any project. Free up to 500 files.</p>
            <a className="btn btn-lime" href="#install">Install Free →</a>
          </div>
        </div>
      </div>
      </Reveal>

      <footer>
        <div className="container footer-inner">
          <span>Vinemap — the context layer for AI coding agents · 100% local</span>
          <nav>
            <a href="#install">Install</a>
            <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">PyPI</a>
            <a href={LINKS.githubDocs} target="_blank" rel="noopener noreferrer">Docs</a>
            <a href="#pricing">Pricing</a>
            <a href="#faq">FAQ</a>
            <a href={LINKS.github} target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href={LINKS.githubIssues} target="_blank" rel="noopener noreferrer">Issues</a>
          </nav>
        </div>
      </footer>

      <a className="chat-pill" href="#faq">💬 Ask Vinemap?</a>
    </>
  );
}
