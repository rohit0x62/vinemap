export const FAQS = [
  {
    q: "Does my code leave my machine?",
    a: "No. The graph, session memory, and context packs are stored in .vinemap/ inside your project. The MCP server runs locally over stdio — no code, no file names, no project data is ever sent externally.",
  },
  {
    q: "Which AI tools does Vinemap work with?",
    a: "Claude Code, Codex CLI, Cursor, Gemini CLI, GitHub Copilot, OpenCode, and any other MCP-compatible agent. The same install works across all of them.",
  },
  {
    q: "Do I need to run something every session?",
    a: "No. Run `vinemap index .` once, then `vinemap connect <agent>` — after that your agent talks to the local server automatically, and the graph re-syncs incrementally as files change.",
  },
  {
    q: "What happens when my files change?",
    a: "Only touched files are re-parsed thanks to content-hash caching, so updates are sub-second on most projects. No manual rebuilds.",
  },
  {
    q: "What do I get in Pro?",
    a: "Up to 1M files per project, crash diagnosis with blast-radius analysis, decision & WHY memory across sessions, coverage confidence scores, and codebase-health tools (circular deps, dead exports). $10/month, cancel anytime.",
  },
  {
    q: "How does Teams work?",
    a: "Teams adds a shared graph across your organization's repos with per-developer views and shared decision memory — self-hosted or in your VPC, priced per seat.",
  },
] as const;
