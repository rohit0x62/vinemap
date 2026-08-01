# Vinemap — The Context Layer for AI Coding Agents

> Working name: **Vinemap** (a vinemap is what grapevines grow on). Rename with a
> find-and-replace across `vinemap`/`Vinemap` when you pick the final brand.

Vinemap builds a **local graph of your codebase** — files, functions, classes,
imports, call edges — and delivers exactly the right context to AI coding agents
(Claude Code, Cursor, Codex CLI, Gemini CLI, Copilot, any MCP client) before they
start exploring. Fewer tokens, better answers, 100% local.

This monorepo contains everything: engine, CLI, MCP server, installers, website,
and the strategy docs for rollout.

## Repository layout

| Path | What it is |
|---|---|
| `engine/` | Python context engine (`vinemap` on PyPI). Zero runtime deps. |
| `engine/vinemap/scanner/` | Project walker + per-language parsers (Python AST, regex fallback for 12 languages, tree-sitter planned) |
| `engine/vinemap/graph/` | Code graph model + `.vinemap/` persistence |
| `engine/vinemap/rank/` | Relevance ranking (lexical + structural + session signals) |
| `engine/vinemap/pack/` | Token-budgeted context packer |
| `engine/vinemap/memory/` | Session memory (touched files, decisions) |
| `engine/vinemap/mcp/` | MCP server (stdio JSON-RPC) with `graph_retrieve`, `graph_read`, `graph_neighbors`, `graph_stats` |
| `website/` | Next.js marketing site (static export) |
| `installers/` | One-line install scripts (macOS/Linux + Windows) |
| `docs/RESEARCH.md` | Competitive landscape, edge & moat analysis |
| `docs/ARCHITECTURE.md` | System design and how each layer works |
| `docs/PRICING.md` | Free / Pro / Teams tier design |
| `docs/ROADMAP.md` | Phased build-and-rollout plan with detailed todos |
| `PROMPT.md` | The detailed master prompt to drive the full build |

## Quick start (engine)

```bash
cd engine
pip install -e ".[dev]"

vinemap index .                      # build the code graph -> .vinemap/
vinemap query "where is auth handled"
vinemap pack  "how do sessions work" --budget 6000
vinemap mcp .                        # stdio MCP server for your agent
```

Wire it into Claude Code / Cursor as an MCP server:

```json
{
  "mcpServers": {
    "vinemap": { "command": "vinemap", "args": ["mcp", "/path/to/project"] }
  }
}
```

## Quick start (website)

```bash
cd website
npm install
npm run dev     # http://localhost:3000
npm run build   # static export to website/out/
```

## Tests

```bash
cd engine && python -m pytest tests/ -q
```

## Status

This is the **v0 base**: a working end-to-end skeleton (index → rank → pack →
MCP) plus the strategy docs. `docs/ROADMAP.md` is the source of truth for what
comes next; `PROMPT.md` is the master prompt to drive each phase.
