# Architecture

## System overview

```
                 ┌──────────────────────────────────────────────┐
                 │                 your project                  │
                 │  source files          .vinemap/              │
                 │                        ├─ graph.json  (map)   │
                 │                        └─ session.json (mem)  │
                 └──────────────┬───────────────────────────────┘
                                │
        ┌───────────────────────┼────────────────────────────┐
        │                   Vinemap engine                    │
        │                                                     │
        │  scanner ──► graph ──► rank ──► pack                │
        │  (walk +     (nodes +  (lexical+ (token-budgeted    │
        │   parse)      edges)   struct+   context pack)      │
        │                        session)                     │
        │                          ▲                          │
        │                       memory (session layer)        │
        └──────────┬──────────────────────────┬──────────────┘
                   │                          │
             CLI (vinemap …)            MCP server (stdio)
                   │                          │
             pre-injection            Claude Code / Cursor /
             into agent prompt        Codex / Gemini / Copilot
```

## The dual graph

**Structural layer** (`vinemap/graph/`): file nodes and symbol nodes; edges for
imports (resolved to actual project files), containment (class → method), and
calls (symbol → callee names). Rebuilt from parsed files; unchanged files are
reused via content hashes so re-index is incremental.

**Session layer** (`vinemap/memory/`): an append-only event log of what the agent
retrieved/read/edited plus recorded decisions. Weights decay with a 6-hour
half-life; edits weigh 2× reads. This is what makes context *compound* across
turns and sessions.

## Pipeline stages

1. **Scanner** (`vinemap/scanner/`) — walks the project (ignore rules +
   `.vinemapignore`), routes each file to the best parser:
   - `PythonParser`: precise stdlib-`ast` extraction — signatures with type
     annotations, docstrings, call names, nesting.
   - `RegexParser`: heuristic coverage for JS/TS, Go, Java, Rust, C/C++, C#,
     Ruby, PHP, Kotlin, Swift.
   - *Planned*: tree-sitter parsers per language (`pip install vinemap[treesitter]`)
     replacing the regex fallback with precise symbols + call edges everywhere.
2. **Graph build** (`vinemap/graph/model.py`) — resolves import specifiers to
   project files (dotted, slashed, and relative forms), builds forward/reverse
   edge maps and a symbol-name index. Persisted as JSON in `.vinemap/graph.json`
   (SQLite planned past ~50k files).
3. **Ranker** (`vinemap/rank/ranker.py`) — three additive signals:
   - *Lexical*: query terms vs paths, symbol names, signatures (exact symbol
     match scores highest).
   - *Structural*: top hits propagate 25% of their score to import neighbors;
     small centrality prior for hub files.
   - *Session*: memory weights boost recently touched files.
4. **Packer** (`vinemap/pack/packer.py`) — emits a `<codebase_context>` block
   under a hard token budget: per-file structured summaries (signatures,
   docstrings, call edges, import/importer lists), then up to 45% of the budget
   as inline code of the top symbols, then recent session decisions.
5. **Delivery** — two modes:
   - *MCP tools* (`vinemap/mcp/server.py`, stdio JSON-RPC): `graph_retrieve`,
     `graph_read`, `graph_neighbors`, `graph_stats`. Works with any MCP client
     today.
   - *Pre-injection* (roadmap phase 2): agent-specific launchers/hooks inject
     the pack into the prompt before the first turn — the zero-tool-call mode
     that is the product's core differentiator.

## Design decisions

- **Stdlib-only core.** `pip install vinemap` has zero dependencies, so
  install is instant, offline-safe, and never breaks on a transitive pin.
  Tree-sitter is an optional extra.
- **JSON persistence first.** Trivially debuggable, fast enough below ~10k files.
  The store module isolates persistence so a SQLite swap is local to one file.
- **Free-tier limit in the engine.** `--max-files` defaults to 500 (Free). Pro
  licensing lifts it; enforcement stays server-side-verifiable via license keys
  (roadmap phase 4).
- **Privacy as an invariant.** No network calls anywhere in the engine. Any
  future telemetry must be opt-in and code-free (event counts only).
