"""GitHub Copilot: repository instructions + VS Code MCP pointer."""

import os
from typing import Tuple

from vinemap.connect import _merge_mcp_json

COPILOT_INSTRUCTIONS = """# Vinemap context for Copilot

This repository is indexed by **Vinemap** (see `.vinemap/`).

When answering questions about this codebase:
- Prefer structural context from the Vinemap MCP server (`graph_retrieve`, `graph_read`, `graph_neighbors`).
- Avoid re-reading large swaths of the repo when a graph query would suffice.
- Session decisions may appear in context packs via `vinemap decide`.

If MCP is configured in `.vscode/mcp.json`, use those tools before broad search.
"""


def setup_copilot(root: str) -> Tuple[bool, str]:
    root = os.path.abspath(root)
    github_dir = os.path.join(root, ".github")
    os.makedirs(github_dir, exist_ok=True)
    instr_path = os.path.join(github_dir, "copilot-instructions.md")
    with open(instr_path, "w", encoding="utf-8") as f:
        f.write(COPILOT_INSTRUCTIONS)

    vscode_dir = os.path.join(root, ".vscode")
    os.makedirs(vscode_dir, exist_ok=True)
    mcp_path = _merge_mcp_json(os.path.join(vscode_dir, "mcp.json"), root)

    return True, (
        f"wrote {instr_path}\n"
        f"wrote {mcp_path}\n"
        "Copilot reads .github/copilot-instructions.md; VS Code MCP uses .vscode/mcp.json."
    )
