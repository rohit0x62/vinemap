"""Gemini CLI: project MCP config + instruction file."""

import os
from typing import Tuple

from vinemap.connect import _merge_mcp_json
from vinemap.graph.store import atomic_write_json

GEMINI_INSTRUCTIONS = """# Vinemap context engine

This project uses **Vinemap** (`.vinemap/` graph index).

Before searching files manually:
1. Use the `vinemap` MCP server — tool `graph_retrieve` with the user's task.
2. Use `graph_read` / `graph_neighbors` for targeted follow-ups.
3. Prefer injected `<codebase_context>` packs over re-exploring the repo.

Record decisions with `vinemap decide "..."` so future sessions stay warm.
"""


def setup_gemini(root: str) -> Tuple[bool, str]:
    root = os.path.abspath(root)
    gemini_dir = os.path.join(root, ".gemini")
    os.makedirs(gemini_dir, exist_ok=True)
    instr_path = os.path.join(gemini_dir, "GEMINI.md")
    with open(instr_path, "w", encoding="utf-8") as f:
        f.write(GEMINI_INSTRUCTIONS)
    mcp_path = _merge_mcp_json(os.path.join(gemini_dir, "settings.json"), root)
    return True, (
        f"wrote {instr_path}\n"
        f"wrote {mcp_path}\n"
        "Run `gemini` in this project — MCP tools load from .gemini/settings.json."
    )
