# vinemap

Local-first, graph-based context engine for AI coding agents. Builds a graph of
your codebase (files, symbols, imports, call edges) and delivers token-budgeted
context packs to Claude Code, Cursor, Codex CLI, and any MCP client.

```bash
pip install vinemap

vinemap index .        # build the code graph -> .vinemap/
vinemap query "where is auth handled"
vinemap pack  "how do sessions work"
vinemap mcp .          # stdio MCP server for your agent
```

Zero runtime dependencies. 100% local — nothing leaves your machine.

See the repository root for full documentation, architecture, and roadmap.
