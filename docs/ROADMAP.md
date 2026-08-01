# Roadmap: Build → Launch → Scale

Phases are sequential; items within a phase can be parallelized. ✅ = done in the
v0 base in this repo.

## Phase 0 — Base (this repo) ✅

- [x] Monorepo: engine, website, installers, docs
- [x] Scanner: walker with ignore rules, content-hash incremental cache
- [x] Parsers: Python (AST-precise), regex fallback for 12 top languages
- [x] Code graph: import resolution (dotted/slashed/relative), symbol index, reverse edges
- [x] Ranker: lexical + structural expansion + session boost
- [x] Context packer: token-budgeted, code-first (45% inline code), decisions section
- [x] Session memory: touch events with time decay, decision log
- [x] MCP server (stdio): graph_retrieve / graph_read / graph_neighbors / graph_stats
- [x] CLI: index, query, pack, stats, mcp, decide; 500-file free-tier default
- [x] Test suite (10 tests) passing
- [x] Installers: install.sh (macOS/Linux), install.ps1 (Windows)
- [x] Marketing site: hero, how-it-works, features, languages, comparison, pricing, FAQ
- [x] Strategy docs: RESEARCH, ARCHITECTURE, PRICING, this roadmap, PROMPT.md

## Phase 1 — Engine to parity (2–4 weeks)

**Parsing & graph**
- [ ] Tree-sitter parsers (optional extra): TS/JS, Go, Java, Rust, C/C++, C#, Ruby, PHP, Kotlin, Swift — precise symbols, call edges, type refs
- [ ] Call-edge resolution across files (name → defining file via symbol index)
- [ ] SQLite store behind the same interface; benchmark JSON→SQLite crossover
- [ ] File watcher (`vinemap watch`): re-index on save, debounced, sub-second
- [ ] Monorepo awareness: package boundaries (package.json / pyproject / go.mod) as graph clusters

**Retrieval quality**
- [ ] BM25-style scoring over identifiers + comments (still dependency-free)
- [ ] Optional local embeddings (extra) as a fourth ranking signal
- [ ] Retrieval eval harness: golden query→files sets on 3 OSS repos (a TS, a Go, a Python one — mirror GrapeRoot's Medusa/Gitea/Sentry choice); track precision@k in CI

**Hardening**
- [x] Security pass: symlinks never followed (dir + file), packer refuses reads outside project root even with a tampered graph.json, MCP input validation (query/path/budget types, budget clamped 500–32k, tool-name sanitized, oversized/malformed frames dropped), atomic writes for graph + session state, corrupt index treated as absent
- [x] `vinemap connect cursor|claude|gemini|codex` — writes/merges project MCP configs (verified: preserves existing servers)
- [x] Package builds clean: sdist + wheel pass `twine check`; fresh-venv E2E on the built wheel passed (index → connect → MCP handshake → retrieval → traversal probe rejected)
- [ ] Publish `vinemap` to PyPI (needs account/credentials — artifacts ready in `engine/dist/`)
- [ ] Windows path handling end-to-end; CI matrix (mac/linux/windows × py3.9–3.13)
- [ ] 100k-file stress test; memory profile; lazy graph loading

## Phase 2 — Agent integrations & pre-injection (the differentiator) (2–3 weeks)

- [ ] `vinemap claude` launcher: writes Claude Code hooks (UserPromptSubmit → inject pack; PreCompact → re-inject; SessionEnd → log tokens)
- [ ] `vinemap cursor`: writes `.cursor/rules` + MCP config into the project
- [ ] `vinemap codex`, `vinemap gemini`, `vinemap copilot`, `vinemap opencode` equivalents
- [ ] Interactive picker: bare `vinemap .` shows agent menu (parity with `graperoot .`)
- [ ] Guardrails: per-turn read budgets, duplicate-read dedup, grep rate-limit hints
- [ ] Token tracker: passive session accounting + `vinemap dashboard` (local web UI)
- [ ] Auto-update: `vinemap --update`, version check on start (single anonymous GET, documented)

## Phase 3 — Launch (1–2 weeks, overlaps phase 2)

- [x] Name the product: **Vinemap** — verified free on PyPI (404), npm (404), and vinemap.dev (no DNS records) as of Aug 2026; rename applied repo-wide. Register the domain + PyPI/npm names ASAP to lock them.
- [ ] Publish GitHub repo (Apache-2.0 engine), CONTRIBUTING, issue templates
- [ ] Docs site (/docs): install, per-agent guides, how-it-works, troubleshooting per OS
- [ ] Benchmarks page: run the eval harness, publish raw prompts + transcripts + methodology (reproducibility is the credibility moat)
- [ ] Deploy website (Vercel/Cloudflare Pages) + install scripts on CDN
- [ ] Community: Discord server, GitHub Discussions
- [ ] Launch posts: Hacker News (Show HN), r/ClaudeAI, r/cursor, X/Twitter dev threads, Product Hunt
- [ ] Feedback loop: in-CLI one-time feedback prompt (opt-in), website form

## Phase 4 — Monetization (2–3 weeks)

- [ ] Ed25519 offline license keys; `vinemap license activate <key>`
- [ ] Stripe checkout + customer portal + webhook → key issuance (small serverless api/)
- [ ] Pro features, in value order:
  - [ ] Crash diagnosis: stack trace → graph walk → root-cause candidates + blast radius
  - [ ] Decision/WHY memory surfaced in packs across sessions
  - [ ] Coverage score per pack
  - [ ] Circular dependency finder + dead export detection
  - [ ] Exhaustive audit mode
  - [ ] 1M-file scale (SQLite + lazy loading from phase 1)
- [ ] Pricing page wired to checkout; trial flow (7 days, card up front like GrapeRoot or keyless trial — decide)

## Phase 5 — Teams (4–8 weeks)

- [ ] Shared graph server (self-hosted Docker + VPC): org repos indexed centrally, per-dev session layers merged
- [ ] Cross-repo retrieval ("where do we validate JWTs across services?")
- [ ] Shared decision memory with attribution
- [ ] SSO (OIDC), audit log, seat management + license server
- [ ] Team pilot program: 3–5 design partners from Discord/launch signups before GA

## Ongoing / growth

- [ ] Comparison content per competitor (vs Repomix, Aider, Continue, Augment, Graphify…) — GrapeRoot's SEO playbook
- [ ] Language coverage expansion via community parser contributions
- [ ] Opt-in anonymous retrieval-quality telemetry (counts only, never code) to tune ranking
- [ ] Case studies with token-savings numbers from real users

## Success metrics

| Stage | Metric | Target |
|---|---|---|
| Launch | GitHub stars / week 1 installs | 500 stars, 1k installs |
| Activation | % installs that index ≥1 project and run ≥5 queries | >40% |
| Retention | week-4 active installs | >25% |
| Revenue | free→Pro conversion | 2–5% |
| Teams | design partners → paid pilots | 3 in first quarter |
