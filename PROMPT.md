# Master Build Prompt

Use this prompt (whole, or one phase at a time) to drive an AI agent — or a team —
through building the full product. It encodes everything learned from the research
in `docs/RESEARCH.md`. The v0 base in this repo already implements Phase 0.

---

## The prompt

You are building **Vinemap** (working name), a local-first, graph-based **context
engine for AI coding agents** — the same category as graperoot.dev, Augment's
Context Engine, and Aider's repo map. Business model: open-core. Free tier for
individuals (500 files/project, no account), Pro at $10/mo (1M files + advanced
intelligence), and custom per-seat Teams (shared org graph, self-hosted/VPC).

### Product thesis (do not drift from this)

1. AI coding agents waste 50%+ of tokens on an "exploration tax": grepping,
   reading, and re-reading files to find context before answering.
2. A structural code graph (files, symbols, imports, call edges) knows which
   files matter *before* the agent asks. Deliver that context up front —
   ideally **pre-injected into the prompt with zero tool calls** — and you cut
   cost dramatically while *improving* answer quality.
3. Non-negotiable invariants:
   - **100% local**: no code, file names, or project data ever leaves the
     machine. No account for the free tier. The engine makes zero network calls.
   - **Zero config**: one install command; one command per project; the tool
     configures each agent itself.
   - **Agent-agnostic**: Claude Code, Cursor, Codex CLI, Gemini CLI, GitHub
     Copilot, OpenCode, and any MCP client — one graph serves all.
   - **Structured summaries over raw dumps**: signatures, call edges,
     docstrings; inline code only for the top-ranked symbols (~45% of budget).
   - **Compounding memory**: session + decision memory makes turn N cheaper and
     smarter than turn 1. This is the moat — prioritize it in every phase.

### Architecture (already scaffolded in `engine/`)

Pipeline: **scanner → graph → ranker → packer → delivery**, plus a session
memory layer. Read `docs/ARCHITECTURE.md` before changing anything. Rules:
- Core engine stays stdlib-only; heavy deps (tree-sitter, embeddings) are
  optional extras.
- Every stage is behind a small interface (parser registry, store module,
  ranking signals) — extend by adding implementations, not by rewriting.
- Every retrieval-quality change must be validated against the eval harness
  (golden query→file sets on three real OSS repos: one TypeScript, one Go, one
  Python) with precision@k tracked in CI.

### Languages

Support the top languages with this priority: Python, TypeScript/JavaScript, Go,
Java, Rust, C/C++, C#, Ruby, PHP, Kotlin, Swift. Python uses stdlib `ast`; the
others start on the regex fallback and graduate to tree-sitter grammars
(`vinemap[treesitter]`) one language at a time, with parser tests per
language on real-world files.

### Deliverables by phase (details in `docs/ROADMAP.md`)

- **Phase 1 — Engine parity**: tree-sitter parsers, resolved call edges, SQLite
  at scale, file watcher, monorepo package clusters, eval harness, PyPI publish,
  Windows/macOS/Linux CI matrix.
- **Phase 2 — Pre-injection (the differentiator)**: per-agent launchers that
  write hooks/configs (Claude Code hooks incl. re-inject on compaction; Cursor
  rules + MCP; Codex/Gemini/Copilot equivalents), interactive `vinemap .`
  picker, read-budget guardrails, passive token tracker + local dashboard,
  auto-update.
- **Phase 3 — Launch**: final name + domain, open-source the engine
  (Apache-2.0), docs site, **reproducible public benchmarks with raw data**
  (the credibility moat), deploy website + CDN install scripts, Discord,
  Show HN / Product Hunt / dev-community launch.
- **Phase 4 — Monetization**: offline Ed25519 license keys, Stripe checkout +
  webhooks, Pro features in value order: crash diagnosis with blast radius →
  decision/WHY memory → coverage score → dep-cycle & dead-export detection →
  exhaustive audit mode → 1M-file scale.
- **Phase 5 — Teams**: self-hosted shared graph server, cross-repo retrieval,
  shared decision memory, SSO/audit/seats, 3–5 design partners before GA.

### Quality bar

- Every module has tests; `python -m pytest engine/tests -q` stays green.
- The website (`website/`) builds statically (`npm run build`); keep it fast,
  dark, modern; every marketing claim must be backed by the benchmarks page.
- Error messages tell the user the fix, not the stack trace.
- Measure everything against the two numbers that sell the product: **% token
  reduction** and **answer-quality win rate** vs. a no-Vinemap baseline.

### What NOT to build

- No cloud indexing of user code, ever (Teams server is self-hosted/VPC).
- No per-token pricing (flat tiers only — this is a positioning weapon against
  Augment's metered pricing).
- No agent of our own — we make existing agents better; never compete with them.

---

## Usage

- One phase per session: "Read PROMPT.md and docs/ROADMAP.md. Execute Phase N.
  Do not start items from later phases."
- For focused work: "Read PROMPT.md. Within the invariants, implement <item>
  from Phase N of docs/ROADMAP.md, with tests."
