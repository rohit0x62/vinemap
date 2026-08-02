# Vinemap Moat & AI Infra Strategy

## Positioning

**Vinemap is local AI context infrastructure** — not another RAG wrapper, not a chat UI.
We sit between the codebase and every AI coding agent, delivering structural context
*before* exploration burns tokens.

## The moat (what competitors cannot copy quickly)

| Layer | Defensibility | Status |
|-------|---------------|--------|
| **Pre-injection hooks** | Zero tool calls on turn 1; requires agent-specific integration depth | ✅ Claude hooks, Cursor rules |
| **Structural code graph** | Imports + calls + symbols beat chunk embeddings on code tasks | ✅ Call edges, BM25 |
| **Reproducible benchmarks** | Public precision@k on golden repos = sales credibility | ✅ `engine/eval/` |
| **Session compounding** | Touch/decision memory makes pack #2 better than pack #1 | ✅ session.json |
| **Local-first + offline license** | No code leaves machine; Pro keys can't be forged without private key | ✅ Ed25519 |
| **Teams shared graph** | Network effect; highest switching cost | 🔜 Phase 5 |

## Differentiators vs commodity

- **vs Repomix / raw dump**: We rank and budget — not 500k tokens of noise.
- **vs vector RAG**: We understand import/call structure, not cosine similarity on chunks.
- **vs MCP-only tools**: Pre-injection means the agent starts informed, not tool-happy.
- **vs cloud context (Augment)**: 100% local; no usage meter on every read.

## Go-to-market sequence

1. **Free tier as distribution** — 500 files, full MCP, session memory. No signup.
2. **Prove savings** — benchmarks page + dashboard token estimates.
3. **Convert on scale** — 500+ file repos need Pro ($10/mo).
4. **Convert on intelligence** — diagnose, health, audit for daily driver devs.
5. **Teams pilots** — shared graph for eng orgs (custom pricing).

## Revenue architecture

```
User → pip install / install.sh → index → quickstart
     → hits 500 file wall OR wants diagnose → Stripe checkout
     → webhook issues VMP1 license → vinemap license activate
     → 1M files + Pro MCP tools + web dashboard
```

Private signing key **never** in the repo. Open source engine + closed issuance = standard open-core.

## Why users pay despite open source

1. Valid license keys require our private key (forgery != bypass in regulated teams).
2. Convenience: `pip install`, Stripe billing, support.
3. Time > $10: maintaining a fork costs more than subscribing.
4. Companies need receipts and compliance.

## Metrics that matter

| Metric | Target | Why |
|--------|--------|-----|
| precision@5 on eval harness | ≥70% | Proves retrieval quality |
| Activation (index + 5 queries) | >40% | Product works |
| Pre-injection adoption | >25% of installs | Moat engagement |
| Free → Pro | 2–5% | Revenue |
| Teams pilots | 3 in Q1 | Infra moat |

## Build priorities (next)

1. Wire Stripe checkout on website → `api/` webhook
2. Tree-sitter parsers for TS/Go (optional extra)
3. SQLite store for 1M-file Pro promise
4. Teams shared graph server (Docker)
5. Comparison SEO + case studies with token savings numbers

## One-line pitch

> Vinemap is the local context layer for AI coding agents — graph-first, pre-injected, and measurable.
