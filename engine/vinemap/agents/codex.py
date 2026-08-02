"""OpenAI Codex CLI: project hint file + global config snippet."""

import os
from typing import Tuple

from vinemap.connect import connect_agent

CODEX_PROJECT_README = """# Vinemap + Codex

This repo is indexed by Vinemap. Add to your **global** `~/.codex/config.toml`:

```toml
[mcp_servers.vinemap]
command = "vinemap"
args = ["mcp", "{root}"]
```

Then run `codex` here. Prefer MCP `graph_retrieve` over blind file search.
"""


def setup_codex(root: str) -> Tuple[bool, str]:
    root = os.path.abspath(root)
    codex_dir = os.path.join(root, ".codex")
    os.makedirs(codex_dir, exist_ok=True)
    readme_path = os.path.join(codex_dir, "VINEMAP.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(CODEX_PROJECT_README.format(root=root))

    # Optional project-local override (Codex builds that honor CWD)
    local_toml = os.path.join(codex_dir, "config.toml")
    if not os.path.isfile(local_toml):
        with open(local_toml, "w", encoding="utf-8") as f:
            f.write(
                '[mcp_servers.vinemap]\n'
                f'command = "vinemap"\n'
                f'args = ["mcp", "{root}"]\n'
            )
        wrote_local = True
    else:
        wrote_local = False

    _wrote, connect_msg = connect_agent("codex", root)
    lines = [f"wrote {readme_path}"]
    if wrote_local:
        lines.append(f"wrote {local_toml}")
    lines.append(connect_msg)
    return True, "\n".join(lines)
