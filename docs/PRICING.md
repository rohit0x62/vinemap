# Pricing & Packaging

Open-core, local-first. The engine is free and open source; value is captured on
scale (file limits), intelligence (Pro features), and collaboration (Teams).

## Tiers

### Free — $0 forever
Target: individual devs, OSS, evaluation. This tier IS the distribution engine.
- Full code graph, ranking, context packs, MCP tools
- All supported languages, session memory
- Up to **500 files** per project
- 100% local, no account required

### Pro — $10/month (7-day free trial, Stripe, cancel anytime)
Target: professional devs on real codebases. Anchored on "pays for itself in
saved tokens in the first week".
- Up to **1M files** per project
- **Crash diagnosis**: paste a stack trace → root-cause candidates + blast radius
  from the call/import graph
- **Decision (WHY) memory** across sessions
- **Coverage score**: how completely the pack covers the question's blast radius
- **Codebase health**: circular dependency finder, dead export detection
- **Exhaustive audit mode**: find-all-occurrences deep scans
- Live token-savings dashboard

### Teams — custom per-seat (target $20–40/seat/mo, annual)
Target: eng teams 10–500. Self-hosted or VPC; the shared graph is the moat.
- Everything in Pro
- **Shared team graph** across org repos (server component, on your infra)
- Per-developer views + shared decision memory ("why is it built this way" answered from the graph)
- Cross-repo retrieval
- SSO, audit logs, priority support, onboarding

## Enforcement model
- Free limits live in the engine defaults (`--max-files 500`).
- Pro: signed offline license key (Ed25519), validated locally — keeps the
  "no account, works offline" promise; Stripe issues/rotates keys.
- Teams: license server bundled with the shared-graph server.

## Why this shape works
- Free tier removes all friction (no signup) → maximizes top of funnel, matches
  GrapeRoot/Aider/Repomix expectations that local tools are free.
- $10 flat undercuts token-metered competitors (Augment charges usage + 40% fee)
  and is an easy personal-card expense.
- Teams monetizes the network effect where switching cost is highest.
