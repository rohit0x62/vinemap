"""Cursor rules + MCP: tell the agent to use Vinemap and prefer graph over grep."""

import os
from typing import Tuple

from vinemap.connect import _merge_mcp_json
from vinemap.graph.store import atomic_write_json

CURSOR_RULE = """---
description: Vinemap code graph context — use before exploring the repo
globs: *
alwaysApply: true
---

# Vinemap context engine

This project is indexed by **Vinemap** (`.vinemap/`). Before grepping or reading files blindly:

1. Call MCP tool `graph_retrieve` with the user's task as the query.
2. Use `graph_read` for one file's symbols/imports; `graph_neighbors` for related files.
3. Prefer the injected `<codebase_context>` packs over re-exploring from scratch.

Vinemap ranks by **structure** (imports, symbols, calls) — not just text similarity.
Session decisions live in packs when recorded via `vinemap decide`.
"""


def setup_cursor(root: str) -> Tuple[bool, str]:
    """Write .cursor/rules and MCP config."""
    root = os.path.abspath(root)
    rules_dir = os.path.join(root, ".cursor", "rules")
    os.makedirs(rules_dir, exist_ok=True)
    rule_path = os.path.join(rules_dir, "vinemap.mdc")
    with open(rule_path, "w", encoding="utf-8") as f:
        f.write(CURSOR_RULE)

    mcp_path = _merge_mcp_json(os.path.join(root, ".cursor", "mcp.json"), root)
    return True, (
        f"wrote {rule_path}\n"
        f"wrote {mcp_path}\n"
        "Reload Cursor — Vinemap rules apply globally; MCP tools available in Settings → MCP."
    )
