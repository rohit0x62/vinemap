"""Agent auto-configuration: wire the Vinemap MCP server into coding agents.

Project-scoped config files are merged, never overwritten: existing servers
and unrelated settings are preserved.
"""

import json
import os
from typing import Tuple

from vinemap.graph.store import atomic_write_json

AGENTS = ("cursor", "claude", "gemini", "codex", "copilot", "opencode")


def _server_entry(root: str) -> dict:
    return {"command": "vinemap", "args": ["mcp", root]}


def _merge_mcp_json(config_path: str, root: str) -> str:
    """Insert/update the vinemap server inside {"mcpServers": {...}}."""
    config: dict = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                config = loaded
        except (json.JSONDecodeError, OSError):
            raise SystemExit(
                f"error: {config_path} exists but is not valid JSON — "
                "fix or remove it, then re-run"
            )
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise SystemExit(f"error: 'mcpServers' in {config_path} is not an object")
    servers["vinemap"] = _server_entry(root)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    atomic_write_json(config_path, config)
    return config_path


def connect_agent(agent: str, root: str) -> Tuple[bool, str]:
    """Configure `agent` for the project at `root`.

    Returns (wrote_file, message).
    """
    root = os.path.abspath(root)
    if agent == "cursor":
        path = _merge_mcp_json(os.path.join(root, ".cursor", "mcp.json"), root)
        return True, (
            f"wrote {path}\n"
            "Cursor will show the 'vinemap' MCP server on next window reload "
            "(Settings → MCP to verify)."
        )
    if agent == "claude":
        path = _merge_mcp_json(os.path.join(root, ".mcp.json"), root)
        return True, (
            f"wrote {path}\n"
            "Claude Code picks up project-scope servers automatically — "
            "run `claude` inside the project and approve the server."
        )
    if agent == "gemini":
        path = _merge_mcp_json(os.path.join(root, ".gemini", "settings.json"), root)
        return True, (
            f"wrote {path}\n"
            "Gemini CLI loads project settings on start — run `gemini` inside the project."
        )
    if agent == "codex":
        snippet = (
            "[mcp_servers.vinemap]\n"
            'command = "vinemap"\n'
            f'args = ["mcp", "{root}"]\n'
        )
        return False, (
            "Codex CLI uses a global config. Add this to ~/.codex/config.toml:\n\n"
            + snippet
            + f"\nOr run `vinemap codex` to write {root}/.codex/config.toml (project-local)."
        )
    if agent == "copilot":
        path = _merge_mcp_json(os.path.join(root, ".vscode", "mcp.json"), root)
        return True, (
            f"wrote {path}\n"
            "Also run `vinemap copilot` for .github/copilot-instructions.md."
        )
    if agent == "opencode":
        path = _merge_mcp_json(os.path.join(root, ".opencode", "mcp.json"), root)
        return True, (
            f"wrote {path}\n"
            "Also run `vinemap opencode` for .opencode/rules/vinemap.md."
        )
    raise SystemExit(f"error: unknown agent '{agent}' (choose from: {', '.join(AGENTS)})")
