# Market Research: Context Engines for AI Coding Agents

*Compiled Aug 2026. Sources: graperoot.dev (product, docs, pro pages), Augment Code
launch posts, Sourcegraph context comparison, Zylos codebase-intelligence research,
Ry Walker code-intelligence tools survey.*

## 1. The category

"Context engines" sit between a codebase and an AI coding agent. The thesis, now
validated across the market: **context architecture matters as much as model
choice**. Augment's benchmarks showed Sonnet + good context beating Opus without
it; Meta's pre-computed context engine cut agent tool calls by 40%.

Three architectural camps:

1. **Index-first** (Cursor's internal index, Sourcegraph Cody, Augment): persistent
   embeddings/graphs built ahead of time. Fast retrieval; needs infrastructure;
   indexes can go stale.
2. **Agentic search** (Claude Code default): no index; the agent greps/reads at
   task time. Zero setup; burns tokens every turn ("exploration tax").
3. **Graph-augmented hybrid** (GrapeRoot, Graphify, Meta internal): structural
   dependency graph + on-demand retrieval. Highest architectural coverage on
   benchmarks. **This is where we play.**

## 2. Reference product: GrapeRoot (graperoot.dev)

The closest template for what we're building. Two IIT Delhi founders, open-core,
~950 GitHub stars, 300+ Discord members, logos from Microsoft/Canva/Elastic users.

**Product mechanics:**
- One-line curl installer → `graperoot .` per project/session; per-agent shortcuts (`dgc`, `dg`).
- Builds a **dual graph**: code map (files/symbols/imports/calls) + session action graph.
- Started as MCP tools; evolved to **pre-injection** — retrieve locally in ms, pack
  a structured summary, inject into the prompt *before* the agent thinks. Zero
  tool-call overhead is their headline architectural insight.
- Context packer: signatures, params, return types, call edges; up to 45% of token
  budget on inline code of top functions.
- Session memory: touched files served with high confidence on later turns;
  decisions carry across sessions via hooks.
- Guardrails: per-turn read budgets, deduped reads, rate-limited fallback greps.
- Local MCP server on ports 8080–8099; hooks re-inject on context compaction.
- Token tracker dashboard; auto-update via Cloudflare R2 CDN.
- 100% local pitch: only outbound call is a version check.

**Pricing:** Free (500 files) / Pro $10/mo, 7-day trial, Stripe (1M files, crash
diagnosis with blast radius, WHY-decision memory, coverage score, model routing,
3D graph viz, dead exports + circular deps, exhaustive audit mode) / Enterprise
custom per-seat, self-hosted or VPC, shared team graph.

**Marketing:** published benchmarks (78 prompts across Medusa/TS, Gitea/Go,
Sentry/Py): 83% max token reduction on debugging, 45–57% avg cost saved, 75%
quality win rate, "2.4× quality per dollar", raw data public. Testimonials incl.
a Meta director. Comparison pages against every adjacent tool. Discord community.
Email-capture for install link. Chat widget.

## 3. Competitive landscape

| Tool | Type | Approach | Local? | Pricing | Weakness we exploit |
|---|---|---|---|---|---|
| **GrapeRoot** | open-core CLI | dual graph + pre-injection | yes | Free/$10/Ent | proprietary engine core; single-dev-scale; no team graph yet |
| **Augment Context Engine** | commercial MCP | semantic index, 400k+ files, cross-repo | local + hosted | token-based +40% fee, $252M raised | enterprise-priced, closed, cloud-leaning; overkill for individuals |
| **Sourcegraph Cody** | enterprise SaaS | SCIP code intel + search RAG | cloud | enterprise | heavy infra, org sales motion, not agent-first |
| **Greptile** | YC SaaS | full-codebase index for PR review | cloud | SaaS | review-only wedge; code must leave machine |
| **Aider repo map** | OSS feature | tree-sitter signatures + PageRank, ~1k tokens | yes | free | rebuilt per message, signatures only, aider-only |
| **Repomix** | OSS CLI | whole-repo dump to XML/MD | yes | free | static, manual, sends everything |
| **Continue.dev** | OSS agent | embedding RAG (@codebase) | yes | free | no structural edges; re-embed on change |
| **Graphify** | OSS/skill | tree-sitter graph via MCP tools (165+ langs) | yes | free | reactive tool calls; manual build/freshness |
| **Sourcebot** | self-hosted | Zoekt search + MCP | yes | free | reactive; needs Docker |
| **RTK / Headroom** | compressors | shrink output / compress context | yes | free/OSS | downstream only — complementary, not competing |
| **Cline** | OSS agent | agentic exploration | yes | free | is the exploration tax |

## 4. Edge — why this product wins deals

1. **Pre-injection beats tool calls.** Everyone else (Graphify, Sourcebot, Augment
   MCP) is reactive: the agent must decide to query, pay round-trip latency and
   protocol tokens. Pre-computing relevance and injecting before the first token
   is measurably cheaper and produces better first answers.
2. **Structural graph beats embeddings.** Import/call edges pull in related files
   that cosine similarity misses (renamed vars, cross-file type flow). No
   re-embedding cost on edit; incremental hash-based re-index is sub-second.
3. **100% local beats cloud.** No SOC2 conversation, no code egress, works in
   air-gapped enterprises where Augment/Greptile/Cody can't even bid. Privacy is
   both a feature and a sales unlock.
4. **Agent-agnostic beats agent-specific.** Aider's map only helps Aider. One
   graph serving Claude Code + Cursor + Codex + Copilot rides every agent's
   growth instead of betting on one.
5. **Zero-config install beats infrastructure.** One command vs Docker Compose
   (Sourcebot) or enterprise onboarding (Augment, Cody).

## 5. Moat — why it stays won

Honest assessment: the *core algorithm* (tree-sitter graph + ranking + packing) is
replicable in weeks. The moat must be built in layers around it:

1. **Compounding session/decision memory** — the longer a team uses it, the more
   WHY-decisions, hotspot weights, and cross-session context accumulate in their
   graph. Switching cost grows with usage. This is the strongest product moat;
   invest here first.
2. **Benchmark credibility** — publish reproducible, raw-data benchmarks on real
   OSS repos (GrapeRoot's playbook: 78 prompts, 3 codebases, LLM judge). First
   mover on *trustworthy numbers* owns the comparison-shopping narrative.
3. **Integration surface** — every agent hook (Claude compaction hooks, Cursor
   rules, Codex profiles, Copilot instructions), every editor, every OS quirk
   handled is grunt work competitors must repeat. The installer *is* moat.
4. **Team graph (network effect)** — a shared org-wide graph with per-dev views
   makes value grow with seats and makes the product a system of record for
   "how our codebase connects + why decisions were made". Individual tools
   can't follow there without rebuilding as infra.
5. **Open-core community** — free local engine drives distribution (stars,
   word-of-mouth, Discord), proprietary Pro/Teams layers capture value.
   Community contributions on language parsers widen coverage faster than any
   closed competitor.
6. **Data flywheel (privacy-safe)** — opt-in anonymous *retrieval quality*
   telemetry (hit/miss, not code) tunes ranking better with every user.

**What is NOT a moat:** the parser, the packer, "we're cheaper", the website.

## 6. Risks

- **Agents internalize context engines.** Claude Code / Cursor could ship a
  built-in graph layer (Cursor already indexes). Mitigation: be the *cross-agent*
  layer + team memory they won't build, move up to team/org value fast.
- **Augment moves down-market.** Their MCP engine free-tier could squeeze the
  middle. Mitigation: local-only + flat pricing vs their token-metered + 40% fee.
- **Benchmark skepticism.** Self-reported numbers are discounted. Mitigation:
  publish raw prompts/transcripts, make the harness open source, invite replication.
- **MCP protocol churn.** Spec evolves quickly. Mitigation: thin protocol adapter
  layer (already isolated in `vinemap/mcp/`).

## 7. Positioning statement

> **Vinemap is the local-first context layer for every AI coding agent.** It
> builds a live graph of your codebase and your team's decisions, and delivers
> exactly the right context before your agent starts thinking — cutting token
> spend 50%+ while improving answer quality. Free for individuals, $10/mo Pro,
> per-seat Teams with a shared org graph. Your code never leaves your machine.
