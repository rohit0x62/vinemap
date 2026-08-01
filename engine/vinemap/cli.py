"""Vinemap CLI.

Commands:
  vinemap index [path]           Build or incrementally refresh the code graph
  vinemap query "..." [path]     Show top-ranked files for a question
  vinemap pack "..." [path]      Print the injectable context pack
  vinemap stats [path]           Index statistics
  vinemap mcp [path]             Run the MCP server on stdio (for agent configs)
  vinemap connect <agent> [path] Auto-configure cursor/claude/gemini/codex
  vinemap decide "..." [path]    Record a session decision (WHY memory)
"""

import argparse
import os
import sys
import time

from vinemap import __version__
from vinemap.connect import AGENTS, connect_agent
from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, load_raw_files, save_graph
from vinemap.mcp.server import McpServer
from vinemap.memory.session import SessionMemory
from vinemap.pack.packer import DEFAULT_BUDGET_TOKENS, build_context_pack, estimate_tokens
from vinemap.rank.ranker import rank_files
from vinemap.scanner.walker import scan_project

FREE_TIER_MAX_FILES = 500  # enforced in the engine; lifted by Pro license


def _root(path: str) -> str:
    root = os.path.abspath(path)
    if not os.path.isdir(root):
        print(f"error: not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    return root


def _load_or_exit(root: str) -> CodeGraph:
    graph = load_graph(root)
    if graph is None:
        print("error: no index found — run `vinemap index` first", file=sys.stderr)
        sys.exit(1)
    return graph


def cmd_index(args: argparse.Namespace) -> None:
    root = _root(args.path)
    t0 = time.time()
    previous = load_raw_files(root)
    files, n_parsed, n_cached = scan_project(root, previous=previous, max_files=args.max_files)
    graph = CodeGraph.build(files)
    save_graph(root, graph)
    s = graph.stats()
    dt = time.time() - t0
    print(
        f"indexed {s['files']} files ({n_parsed} parsed, {n_cached} cached) "
        f"— {s['symbols']} symbols, {s['import_edges']} import edges in {dt:.2f}s"
    )
    langs = ", ".join(f"{k}:{v}" for k, v in s["languages"].items())
    print(f"languages: {langs}")


def cmd_query(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    memory = SessionMemory(root)
    ranked = rank_files(graph, args.query, k=args.k, memory=memory)
    if not ranked:
        print("no matches")
        return
    for path, score in ranked:
        print(f"{score:8.2f}  {path}")


def cmd_pack(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    memory = SessionMemory(root)
    pack, included = build_context_pack(
        root, graph, args.query, budget_tokens=args.budget, memory=memory
    )
    if not pack:
        print("no matches", file=sys.stderr)
        sys.exit(1)
    print(pack)
    print(
        f"\n[{len(included)} files, ~{estimate_tokens(pack)} tokens]",
        file=sys.stderr,
    )


def cmd_stats(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    s = graph.stats()
    print(f"files:        {s['files']}")
    print(f"symbols:      {s['symbols']}")
    print(f"import edges: {s['import_edges']}")
    for lang, n in s["languages"].items():
        print(f"  {lang}: {n}")


def cmd_mcp(args: argparse.Namespace) -> None:
    root = _root(args.path)
    if load_graph(root) is None:
        # auto-index on first MCP start so agents never see an empty graph
        files, _, _ = scan_project(root, max_files=args.max_files)
        save_graph(root, CodeGraph.build(files))
    McpServer(root).serve_stdio()


def cmd_connect(args: argparse.Namespace) -> None:
    root = _root(args.path)
    if load_graph(root) is None:
        files, _, _ = scan_project(root, max_files=FREE_TIER_MAX_FILES)
        save_graph(root, CodeGraph.build(files))
        print(f"indexed {root} (first run)")
    _wrote, message = connect_agent(args.agent, root)
    print(message)


def cmd_decide(args: argparse.Namespace) -> None:
    root = _root(args.path)
    memory = SessionMemory(root)
    memory.record_decision(args.text)
    memory.save()
    print("decision recorded")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vinemap",
        description="Vinemap — local-first, graph-based context engine for AI coding agents",
    )
    parser.add_argument("--version", action="version", version=f"vinemap {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="build or refresh the code graph")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--max-files", type=int, default=FREE_TIER_MAX_FILES)
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("query", help="rank relevant files for a question")
    p.add_argument("query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("-k", type=int, default=10)
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("pack", help="print an injectable context pack")
    p.add_argument("query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--budget", type=int, default=DEFAULT_BUDGET_TOKENS)
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("stats", help="index statistics")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("mcp", help="run the MCP server on stdio")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--max-files", type=int, default=FREE_TIER_MAX_FILES)
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser("connect", help="configure an AI agent to use vinemap")
    p.add_argument("agent", choices=AGENTS)
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_connect)

    p = sub.add_parser("decide", help="record a session decision")
    p.add_argument("text")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_decide)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
