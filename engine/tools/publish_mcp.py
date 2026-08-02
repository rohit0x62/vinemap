#!/usr/bin/env python3
"""MCP server for secure Vinemap PyPI publishing.

Add to ~/.cursor/mcp.json (never commit your token):

{
  "mcpServers": {
    "vinemap-publish": {
      "command": "python3",
      "args": ["/absolute/path/to/vinemap/engine/tools/publish_mcp.py"],
      "env": {
        "PYPI_API_TOKEN": "pypi-AgEIcHlwaS5vcmcC..."
      }
    }
  }
}

Tools never accept tokens as arguments — only PYPI_API_TOKEN / TWINE_PASSWORD / ~/.config/vinemap/pypi-token.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Allow running without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.pypi_publish import (  # noqa: E402
    PublishError,
    build_package,
    publish,
    status_report,
)

PROTOCOL_VERSION = "2024-11-05"
MAX_LINE_BYTES = 2_000_000

TOOLS = [
    {
        "name": "pypi_status",
        "description": (
            "Show local pyproject version vs PyPI and whether a token is configured "
            "(never returns the token itself)."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "pypi_build",
        "description": "Build wheel + sdist and run twine check. Does not upload.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keep_dist": {
                    "type": "boolean",
                    "default": False,
                    "description": "Keep existing dist/ files before building",
                }
            },
        },
    },
    {
        "name": "pypi_publish",
        "description": (
            "Build and upload to PyPI. Requires confirm exactly matching version in pyproject.toml. "
            "Token must be in MCP env (PYPI_API_TOKEN) — never pass token here."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confirm": {
                    "type": "string",
                    "description": "Must equal the version string in engine/pyproject.toml (e.g. 0.1.2)",
                },
                "skip_build": {
                    "type": "boolean",
                    "default": False,
                    "description": "Upload existing dist/ artifacts without rebuilding",
                },
            },
            "required": ["confirm"],
        },
    },
]


def _result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


class PublishMcpServer:
    def tool_pypi_status(self, _args: Dict[str, Any]) -> str:
        return json.dumps(status_report(), indent=2)

    def tool_pypi_build(self, args: Dict[str, Any]) -> str:
        keep_dist = bool(args.get("keep_dist", False))
        artifacts = build_package(clean=not keep_dist)
        return json.dumps({"built": [a.name for a in artifacts]}, indent=2)

    def tool_pypi_publish(self, args: Dict[str, Any]) -> str:
        confirm = args.get("confirm")
        if not isinstance(confirm, str) or not confirm.strip():
            raise PublishError("'confirm' must be the exact version string from pyproject.toml")
        skip_build = bool(args.get("skip_build", False))
        report = publish(confirm=confirm.strip(), skip_build=skip_build)
        return json.dumps(report, indent=2)

    def handle(self, msg: dict) -> Optional[dict]:
        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        if method == "initialize":
            return _result(msg_id, {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "vinemap-publish", "version": "1.0.0"},
            })
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _result(msg_id, {"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name", "")
            if not isinstance(name, str) or not name.replace("_", "").isalnum():
                return _error(msg_id, -32602, "Invalid tool name")
            args = params.get("arguments")
            if not isinstance(args, dict):
                args = {}
            handler = getattr(self, f"tool_{name}", None)
            if handler is None:
                return _error(msg_id, -32601, f"Unknown tool: {name}")
            try:
                text = handler(args)
            except Exception as exc:
                return _result(msg_id, {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                })
            return _result(msg_id, {"content": [{"type": "text", "text": text}]})
        if msg_id is not None:
            return _error(msg_id, -32601, f"Method not found: {method}")
        return None

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            if len(line) > MAX_LINE_BYTES:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue
            response = self.handle(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    PublishMcpServer().serve_stdio()
