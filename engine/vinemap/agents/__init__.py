"""Agent-specific setup: hooks, rules, and pre-injection configs."""

from vinemap.agents.claude import setup_claude
from vinemap.agents.codex import setup_codex
from vinemap.agents.copilot import setup_copilot
from vinemap.agents.cursor import setup_cursor
from vinemap.agents.gemini import setup_gemini
from vinemap.agents.opencode import setup_opencode

AGENT_SETUP = {
    "claude": setup_claude,
    "cursor": setup_cursor,
    "gemini": setup_gemini,
    "codex": setup_codex,
    "copilot": setup_copilot,
    "opencode": setup_opencode,
}

__all__ = [
    "AGENT_SETUP",
    "setup_claude",
    "setup_cursor",
    "setup_gemini",
    "setup_codex",
    "setup_copilot",
    "setup_opencode",
]
