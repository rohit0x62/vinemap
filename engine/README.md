# Vinemap — Local Code Graph & MCP Context for AI Coding Agents

[![PyPI](https://img.shields.io/pypi/v/vinemap)](https://pypi.org/project/vinemap/)
[![Python](https://img.shields.io/pypi/pyversions/vinemap)](https://pypi.org/project/vinemap/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rohit0x62/vinemap/blob/main/LICENSE)

**Vinemap** builds a **local code graph** of your repository and delivers **token-budgeted context packs** to AI coding agents — Claude Code, Cursor, Codex CLI, Gemini CLI, Copilot, and any MCP client.

Stop wasting tokens on blind exploration. Vinemap ranks the right files *before* your agent's first tool call.

## Install

```bash
pip install vinemap
```

Python 3.9+. **Zero runtime dependencies.**

## Quick start

```bash
vinemap index .                              # build code graph → .vinemap/
vinemap query "where is auth handled"        # ranked search
vinemap pack  "how do sessions work" --budget 6000
vinemap mcp .                                # MCP server (stdio)
vinemap connect cursor                       # auto-configure Cursor
```

## MCP integration

```json
{
  "mcpServers": {
    "vinemap": {
      "command": "vinemap",
      "args": ["mcp", "/path/to/project"]
    }
  }
}
```

**Tools:** `graph_retrieve` · `graph_read` · `graph_neighbors` · `graph_stats`

## Why Vinemap?

- **Graph-native context** — files, symbols, imports, call edges (not just text chunks)
- **Token-budgeted packs** — `<codebase_context>` blocks sized to your budget
- **Session memory** — remembers touched files and decisions across turns
- **100% local** — nothing leaves your machine
- **MCP-native** — works with Cursor, Claude Code, Codex, Gemini, and more

## Supported languages

Python (AST), TypeScript, JavaScript, Go, Rust, Java, C/C++, C#, Ruby, PHP, Kotlin, Swift.

## Links

- **GitHub:** [github.com/rohit0x62/vinemap](https://github.com/rohit0x62/vinemap)
- **Website:** [vinemap.xyz](https://vinemap.xyz)
- **Docs:** [vinemap.xyz/docs](https://vinemap.xyz/docs)
- **Benchmarks:** [vinemap.xyz/benchmarks](https://vinemap.xyz/benchmarks)
- **Discussions:** [github.com/rohit0x62/vinemap/discussions](https://github.com/rohit0x62/vinemap/discussions)
- **Roadmap:** [docs/ROADMAP.md](../docs/ROADMAP.md)

## License

Apache-2.0
