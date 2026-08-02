"""Minimal MCP server (stdio, JSON-RPC 2.0) exposing the code graph.

Implements the subset of the Model Context Protocol needed by Claude Code,
Cursor, Codex CLI, and other MCP clients: initialize, tools/list, tools/call.

Tools:
  graph_retrieve  — ranked context pack for a natural-language query
  graph_read      — structured summary (and optional code) for one file
  graph_neighbors — import/imported-by edges for a file
  graph_stats     — index size, language breakdown
"""

import json
import os
import sys
from typing import Any, Dict, Optional

from vinemap import __version__
from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph
from vinemap.memory.session import SessionMemory
from vinemap.guardrails import Guardrails
from vinemap.pack.packer import build_context_pack, estimate_tokens
from vinemap.pro.audit import audit_symbol
from vinemap.pro.diagnose import diagnose_stack_trace, format_diagnosis
from vinemap.pro.health import find_circular_imports, find_dead_exports
from vinemap.rank.ranker import rank_files

PROTOCOL_VERSION = "2024-11-05"

MAX_QUERY_CHARS = 4000
MIN_BUDGET_TOKENS = 500
MAX_BUDGET_TOKENS = 32000
MAX_LINE_BYTES = 2_000_000  # reject pathological JSON-RPC frames


def _clean_query(args: Dict[str, Any]) -> str:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("'query' must be a non-empty string")
    return query.strip()[:MAX_QUERY_CHARS]


def _clean_budget(args: Dict[str, Any]) -> int:
    raw = args.get("budget_tokens", 6000)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise ValueError("'budget_tokens' must be a number")
    return max(MIN_BUDGET_TOKENS, min(int(raw), MAX_BUDGET_TOKENS))


def _clean_path(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("'path' must be a non-empty string")
    return path.strip()

TOOLS = [
    {
        "name": "graph_retrieve",
        "description": (
            "Retrieve a compact, token-budgeted context pack of the most relevant "
            "files, symbols, and code for a natural-language question about this "
            "codebase. Use this INSTEAD of exploring with grep/read."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question or task"},
                "budget_tokens": {"type": "integer", "default": 6000},
            },
            "required": ["query"],
        },
    },
    {
        "name": "graph_read",
        "description": "Structured summary of one file: symbols, signatures, imports, importers.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "graph_neighbors",
        "description": "Files this file imports and files that import it.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "graph_stats",
        "description": "Index statistics: file count, symbol count, edges, languages.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

PRO_TOOLS = [
    {
        "name": "graph_diagnose",
        "description": "Analyze a stack trace → root-cause files + blast radius from the call/import graph.",
        "inputSchema": {
            "type": "object",
            "properties": {"trace": {"type": "string", "description": "Stack trace text"}},
            "required": ["trace"],
        },
    },
    {
        "name": "graph_health",
        "description": "Circular import cycles and likely dead exports.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "graph_audit",
        "description": "Exhaustive find-all for a symbol name across the codebase.",
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
]


class McpServer:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.graph: Optional[CodeGraph] = load_graph(self.root)
        self.memory = SessionMemory(self.root)
        self.guardrails = Guardrails()

    def _tools_list(self) -> list:
        return list(TOOLS) + list(PRO_TOOLS)

    # -- tool implementations ------------------------------------------------

    def _require_graph(self) -> CodeGraph:
        if self.graph is None:
            raise RuntimeError("No index found. Run `vinemap index` in the project first.")
        return self.graph

    def tool_graph_retrieve(self, args: Dict[str, Any]) -> str:
        ok, hint = self.guardrails.check_retrieve()
        if not ok:
            raise ValueError(hint or "retrieve budget exhausted")
        self.guardrails.record_retrieve()
        graph = self._require_graph()
        query = _clean_query(args)
        pack, included = build_context_pack(
            self.root,
            graph,
            query,
            budget_tokens=_clean_budget(args),
            memory=self.memory,
            include_coverage=True,
        )
        if pack:
            self.memory.record_tokens(estimate_tokens(pack), "retrieve")
            self.memory.save()
        if not pack:
            ranked = rank_files(graph, query, k=5, project_root=self.root)
            if not ranked:
                stats = graph.stats()
                return (
                    "No files in the graph matched this query. "
                    f"The index covers {stats['files']} files. Try more specific "
                    "identifiers (function/class/file names), or use graph_stats "
                    "and graph_read to explore."
                )
            return "No strong matches. Closest files: " + ", ".join(p for p, _ in ranked)
        return pack

    def tool_graph_read(self, args: Dict[str, Any]) -> str:
        graph = self._require_graph()
        path = _clean_path(args)
        if path not in graph.files:
            return f"File not in index: {path}"
        ok, hint = self.guardrails.check_read(path)
        if not ok:
            raise ValueError(hint or "read budget exhausted")
        self.guardrails.record_read(path)
        pf = graph.files[path]
        nb = graph.neighbors(path)
        self.memory.touch(path, "read")
        self.memory.save()
        lines = [f"{path} ({pf.language}, {pf.line_count} lines)"]
        lines.append(f"imports: {nb['imports']}")
        lines.append(f"imported_by: {nb['imported_by']}")
        if nb.get("calls"):
            lines.append(f"calls: {nb['calls']}")
        if nb.get("called_by"):
            lines.append(f"called_by: {nb['called_by']}")
        if hint:
            lines.append(f"hint: {hint}")
        grep_hint = self.guardrails.grep_hint()
        if grep_hint:
            lines.append(f"hint: {grep_hint}")
        for s in pf.symbols:
            lines.append(f"  L{s.line_start}-{s.line_end} {s.signature or s.name} [{s.kind}]")
        return "\n".join(lines)

    def tool_graph_diagnose(self, args: Dict[str, Any]) -> str:
        trace = args.get("trace", "")
        if not isinstance(trace, str) or not trace.strip():
            raise ValueError("'trace' must be a non-empty string")
        report = diagnose_stack_trace(self._require_graph(), trace)
        return format_diagnosis(report)

    def tool_graph_health(self, _args: Dict[str, Any]) -> str:
        graph = self._require_graph()
        cycles = find_circular_imports(graph)
        dead = find_dead_exports(graph)
        lines = [f"circular_imports: {len(cycles)}", f"dead_exports: {len(dead)}"]
        for c in cycles[:5]:
            lines.append(f"cycle: {' → '.join(c)}")
        for d in dead[:10]:
            lines.append(f"dead: {d['path']}:{d['line']} {d['symbol']}")
        return "\n".join(lines)

    def tool_graph_audit(self, args: Dict[str, Any]) -> str:
        symbol = args.get("symbol", "")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("'symbol' required")
        hits = audit_symbol(self._require_graph(), self.root, symbol.strip())
        if not hits:
            return f"No hits for {symbol!r}"
        return "\n".join(f"{h['path']}:{h['line']} [{h['kind']}] {h['detail']}" for h in hits)

    def tool_graph_neighbors(self, args: Dict[str, Any]) -> str:
        graph = self._require_graph()
        return json.dumps(graph.neighbors(_clean_path(args)), indent=2)

    def tool_graph_stats(self, _args: Dict[str, Any]) -> str:
        return json.dumps(self._require_graph().stats(), indent=2)

    # -- JSON-RPC plumbing ----------------------------------------------------

    def handle(self, msg: dict) -> Optional[dict]:
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params")
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            return _result(msg_id, {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "vinemap", "version": __version__},
            })
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _result(msg_id, {"tools": self._tools_list()})
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
            except Exception as exc:  # surface tool failures as MCP tool errors
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


def _result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
