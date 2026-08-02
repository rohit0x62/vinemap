"""Claude Code hooks: inject context before each prompt and on compaction."""

import json
import os
from typing import Tuple

from vinemap.connect import _merge_mcp_json
from vinemap.graph.store import atomic_write_json


def _inject_hook_script(root: str) -> str:
    return f'''#!/usr/bin/env bash
# Vinemap pre-injection hook — auto-generated
set -euo pipefail
ROOT="{root}"
PAYLOAD=$(cat)
PROMPT=$(echo "$PAYLOAD" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('prompt') or d.get('user_message') or d.get('message') or '')
" 2>/dev/null || true)
[ -z "$PROMPT" ] && exit 0
exec vinemap inject "$PROMPT" "$ROOT"
'''


def _session_end_script(root: str) -> str:
    return f'''#!/usr/bin/env bash
# Vinemap session token log — auto-generated
set -euo pipefail
ROOT="{root}"
vinemap dashboard "$ROOT" 2>/dev/null | tail -5 >&2 || true
exit 0
'''


def _hooks_config(root: str) -> dict:
    inject_path = os.path.join(root, ".claude", "hooks", "vinemap-inject.sh")
    session_path = os.path.join(root, ".claude", "hooks", "vinemap-session-end.sh")
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": inject_path}],
                }
            ],
            "PreCompact": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": inject_path}],
                }
            ],
            "SessionEnd": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": session_path}],
                }
            ],
        }
    }


def setup_claude(root: str) -> Tuple[bool, str]:
    """Write Claude Code hooks + MCP config for pre-injection."""
    root = os.path.abspath(root)
    hooks_dir = os.path.join(root, ".claude", "hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    inject_path = os.path.join(hooks_dir, "vinemap-inject.sh")
    with open(inject_path, "w", encoding="utf-8") as f:
        f.write(_inject_hook_script(root))
    os.chmod(inject_path, 0o755)

    session_path = os.path.join(hooks_dir, "vinemap-session-end.sh")
    with open(session_path, "w", encoding="utf-8") as f:
        f.write(_session_end_script(root))
    os.chmod(session_path, 0o755)

    settings_path = os.path.join(root, ".claude", "settings.json")
    settings: dict = {}
    if os.path.isfile(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            settings = loaded
    settings.update(_hooks_config(root))
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    atomic_write_json(settings_path, settings)

    mcp_path = _merge_mcp_json(os.path.join(root, ".mcp.json"), root)
    return True, (
        f"wrote {inject_path}\n"
        f"wrote {session_path}\n"
        f"wrote {settings_path} (UserPromptSubmit + PreCompact + SessionEnd hooks)\n"
        f"wrote {mcp_path}\n"
        "Run `claude` in this project — context injects before each turn."
    )
