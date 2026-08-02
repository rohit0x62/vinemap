# Vinemap — Local Code Graph & MCP Context Engine for AI Coding Agents

[![PyPI](https://img.shields.io/pypi/v/vinemap)](https://pypi.org/project/vinemap/)
[![Python](https://img.shields.io/pypi/pyversions/vinemap)](https://pypi.org/project/vinemap/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/rohit0x62/vinemap?style=social)](https://github.com/rohit0x62/vinemap)

**Vinemap** is a **local-first, graph-based context engine** for AI coding agents. It indexes your codebase into a searchable code graph — files, functions, classes, imports, and call edges — then delivers **token-budgeted context packs** to Claude Code, Cursor, Codex CLI, Gemini CLI, Copilot, and any MCP client **before your agent starts exploring**.

Fewer tokens. Better answers. Nothing leaves your machine.

- **PyPI:** [pypi.org/project/vinemap](https://pypi.org/project/vinemap/)
- **GitHub:** [github.com/rohit0x62/vinemap](https://github.com/rohit0x62/vinemap)
- **Website:** [vinemap.xyz](https://vinemap.xyz)
- **Docs:** [vinemap.xyz/docs](https://vinemap.xyz/docs)
- **Benchmarks:** [vinemap.xyz/benchmarks](https://vinemap.xyz/benchmarks)
- **Discussions:** [github.com/rohit0x62/vinemap/discussions](https://github.com/rohit0x62/vinemap/discussions)

---

## Why Vinemap?

AI coding agents waste time and tokens reading the wrong files. They grep, skim READMEs, and chase imports — burning context window on exploration instead of solving your task.

Vinemap fixes that by building a **persistent code graph** of your repo and ranking the most relevant files *before* the first tool call:

| Without Vinemap | With Vinemap |
|---|---|
| Agent explores blindly | Agent starts with the right files |
| High token burn on reads | Token-budgeted context packs |
| Context lost between sessions | Session memory (touched files, decisions) |
| Cloud dependency | 100% local — stdlib-only core |

Works with **Model Context Protocol (MCP)** — the open standard used by Cursor, Claude Code, and other agent IDEs.

---

## Install

```bash
pip install vinemap
```

One-line installers:

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/rohit0x62/vinemap/main/installers/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/rohit0x62/vinemap/main/installers/install.ps1 | iex
```

**Requirements:** Python 3.9+. Zero runtime dependencies for the core engine.

---

## Quick start

```bash
vinemap index .                              # build code graph → .vinemap/
vinemap query "where is auth handled"        # ranked file search
vinemap pack  "how do sessions work" --budget 6000   # token-budgeted context pack
vinemap mcp .                                # stdio MCP server for your agent
vinemap connect cursor                       # auto-configure Cursor MCP
vinemap connect claude                       # auto-configure Claude Code MCP
```

### Connect to Cursor or Claude Code (MCP)

Add to your MCP config, or run `vinemap connect cursor` / `vinemap connect claude`:

```json
{
  "mcpServers": {
    "vinemap": {
      "command": "vinemap",
      "args": ["mcp", "/path/to/your/project"]
    }
  }
}
```

### MCP tools

| Tool | Description |
|---|---|
| `graph_retrieve` | Rank and return relevant files for a natural-language query |
| `graph_read` | Read a file from the indexed project |
| `graph_neighbors` | Traverse import/call edges from a symbol or file |
| `graph_stats` | Index stats — file count, symbol count, languages |

---

## Features

- **Code graph indexing** — Python AST parsing + regex fallback for 12 languages (TypeScript, Go, Rust, Java, and more)
- **Relevance ranking** — lexical matching + structural expansion + session boost
- **Context packer** — emits `<codebase_context>` blocks within a token budget
- **Session memory** — tracks touched files and decisions across agent turns
- **MCP server** — stdio JSON-RPC, works with any MCP-compatible agent
- **Agent auto-config** — `vinemap connect cursor|claude|gemini|codex`
- **Privacy-first** — all indexing and retrieval runs locally; no cloud, no telemetry in the core

---

## Supported agents & editors

Vinemap works with any tool that supports MCP or can consume a context pack:

- [Cursor](https://cursor.com)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [OpenAI Codex CLI](https://github.com/openai/codex)
- [Google Gemini CLI](https://github.com/google-gemini/gemini-cli)
- GitHub Copilot, OpenCode, and custom MCP clients

---

## Repository layout

| Path | Description |
|---|---|
| [`engine/`](engine/) | Python package (`vinemap` on PyPI). Zero runtime deps. |
| [`engine/vinemap/scanner/`](engine/vinemap/scanner/) | Project walker + language parsers |
| [`engine/vinemap/graph/`](engine/vinemap/graph/) | Code graph model + `.vinemap/` persistence |
| [`engine/vinemap/rank/`](engine/vinemap/rank/) | Relevance ranking engine |
| [`engine/vinemap/pack/`](engine/vinemap/pack/) | Token-budgeted context packer |
| [`engine/vinemap/memory/`](engine/vinemap/memory/) | Session memory |
| [`engine/vinemap/mcp/`](engine/vinemap/mcp/) | MCP server (stdio) |
| [`installers/`](installers/) | One-line install scripts |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Build & launch roadmap |

---

## Development

```bash
git clone https://github.com/rohit0x62/vinemap.git
cd vinemap/engine
pip install -e ".[dev]"
python -m pytest tests/ -q
```

Build and publish:

```bash
python -m build
twine check dist/*
```

---

## FAQ

**Is Vinemap free?**  
Yes. The core engine is open source (Apache-2.0) and completely free for individual developers — no file limits, no account required. All features (diagnosis, audit, health checks, MCP tools) are included. Teams plans for orgs are coming later.

**Does Vinemap send my code to the cloud?**  
No. Indexing, ranking, and packing all run on your machine. The `.vinemap/` index stays in your project directory.

**How is this different from RAG or vector search?**  
Vinemap uses a **structural code graph** (imports, symbols, call edges) rather than embedding chunks. It's faster, works offline, and understands code relationships — not just text similarity.

**What languages are supported?**  
Python (full AST), plus regex-based symbol extraction for TypeScript, JavaScript, Go, Rust, Java, C/C++, C#, Ruby, PHP, Kotlin, and Swift. Tree-sitter parsers are on the roadmap.

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Status

**v0.1.2** — working end-to-end: index → rank → pack → MCP. Free for individual developers; Teams pricing coming later.
