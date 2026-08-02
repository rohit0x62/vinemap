"""OpenCode agent: project rules + MCP config."""

import os
from typing import Tuple

from vinemap.connect import _merge_mcp_json

OPENCODE_RULE = """---
description: Vinemap graph-first context
alwaysApply: true
---

# Vinemap

Use MCP server **vinemap** before exploring this repo:
- `graph_retrieve` — ranked context pack for the task
- `graph_read` — symbols/imports for one file
- `graph_neighbors` — related files via imports/calls

Prefer graph tools over grep/find when the index exists (`.vinemap/`).
"""


def setup_opencode(root: str) -> Tuple[bool, str]:
    root = os.path.abspath(root)
    rules_dir = os.path.join(root, ".opencode", "rules")
    os.makedirs(rules_dir, exist_ok=True)
    rule_path = os.path.join(rules_dir, "vinemap.md")
    with open(rule_path, "w", encoding="utf-8") as f:
        f.write(OPENCODE_RULE)

    mcp_path = _merge_mcp_json(os.path.join(root, ".opencode", "mcp.json"), root)
    return True, (
        f"wrote {rule_path}\n"
        f"wrote {mcp_path}\n"
        "OpenCode loads .opencode/rules and MCP from .opencode/mcp.json."
    )
