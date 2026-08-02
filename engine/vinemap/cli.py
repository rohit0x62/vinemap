"""Vinemap CLI.

Commands:
  vinemap index [path]           Build or incrementally refresh the code graph
  vinemap query "..." [path]     Show top-ranked files for a question
  vinemap pack "..." [path]      Print the injectable context pack
  vinemap stats [path]           Index statistics
  vinemap mcp [path]             Run the MCP server on stdio (for agent configs)
  vinemap connect <agent> [path] Auto-configure cursor/claude/gemini/codex/copilot/opencode
  vinemap cursor|claude|gemini|... [path]  Full setup (hooks/rules + MCP) for that agent
  vinemap dashboard [path]       Session stats; add --web for local UI
  vinemap inject "..." [path]    Build injection pack (agent hooks)
  vinemap setup <agent> [path]   Same as agent-specific launchers above
  vinemap teams connect <url>    Teams: link project to shared graph server
  vinemap teams push/retrieve    Teams: sync graphs + cross-repo search
  vinemap decide "..." [path]    Record a session decision (WHY memory)
"""

import argparse
import os
import sys
import time
from typing import Optional

from vinemap import __version__
from vinemap.agents import AGENT_SETUP
from vinemap.connect import AGENTS, connect_agent
from vinemap.feedback import maybe_prompt_feedback, open_feedback
from vinemap.graph.model import CodeGraph
from vinemap.graph.store import (
    get_store_backend,
    load_graph,
    load_raw_files,
    migrate_to_sqlite,
    save_graph,
    set_store_backend,
)
from vinemap.license import (
    DEFAULT_MAX_FILES,
    current_tier,
    effective_max_files,
    license_status_text,
    load_stored_license,
    parse_and_verify_key,
    require_teams,
    save_license,
)
from vinemap.mcp.server import McpServer
from vinemap.memory.session import SessionMemory
from vinemap.pack.packer import DEFAULT_BUDGET_TOKENS, build_context_pack, estimate_tokens
from vinemap.pro.audit import audit_symbol
from vinemap.pro.diagnose import diagnose_stack_trace, format_diagnosis
from vinemap.pro.health import find_circular_imports, find_dead_exports
from vinemap.rank.ranker import rank_files
from vinemap.inject import build_injection_pack, extract_query_from_prompt
from vinemap.scanner.monorepo import detect_clusters
from vinemap.scanner.parsers import using_treesitter
from vinemap.scanner.walker import scan_project
from vinemap.watch import watch_project

DEFAULT_INDEX_MAX_FILES = DEFAULT_MAX_FILES


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
    if args.store:
        set_store_backend(root, args.store)
    t0 = time.time()
    previous = load_raw_files(root)
    max_files = effective_max_files(args.max_files)
    files, n_parsed, n_cached = scan_project(root, previous=previous, max_files=max_files)
    graph = CodeGraph.build(files)
    path = save_graph(root, graph)
    s = graph.stats()
    dt = time.time() - t0
    parser_note = "tree-sitter" if using_treesitter() else "regex"
    store_note = get_store_backend(root)
    if store_note == "auto" and path.endswith(".db"):
        store_note = "auto→sqlite"
    print(
        f"indexed {s['files']} files ({n_parsed} parsed, {n_cached} cached) "
        f"— {s['symbols']} symbols, {s['import_edges']} import edges in {dt:.2f}s"
    )
    langs = ", ".join(f"{k}:{v}" for k, v in s["languages"].items())
    print(f"languages: {langs}")
    print(f"parser: {parser_note}  store: {store_note}  → {os.path.basename(path)}")


def cmd_query(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    memory = SessionMemory(root)
    ranked = rank_files(graph, args.query, k=args.k, memory=memory, project_root=root)
    if not ranked:
        print("no matches")
        return
    for path, score in ranked:
        print(f"{score:8.2f}  {path}")


def cmd_pack(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    memory = SessionMemory(root)
    include_coverage = args.coverage
    pack, included = build_context_pack(
        root,
        graph,
        args.query,
        budget_tokens=args.budget,
        memory=memory,
        include_coverage=include_coverage,
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
    if "call_edges" in s:
        print(f"call edges:  {s['call_edges']}")
    print(f"store:        {get_store_backend(root)}")
    print(f"parser:       {'tree-sitter' if using_treesitter() else 'regex'}")
    for lang, n in s["languages"].items():
        print(f"  {lang}: {n}")


def cmd_store_migrate(args: argparse.Namespace) -> None:
    root = _root(args.path)
    db = migrate_to_sqlite(root)
    if db:
        print(f"migrated to SQLite: {db}")
    else:
        print("error: no graph.json to migrate", file=sys.stderr)
        sys.exit(1)


def cmd_mcp(args: argparse.Namespace) -> None:
    root = _root(args.path)
    if load_graph(root) is None:
        # auto-index on first MCP start so agents never see an empty graph
        max_files = effective_max_files(args.max_files)
        files, _, _ = scan_project(root, max_files=max_files)
        save_graph(root, CodeGraph.build(files))
    McpServer(root).serve_stdio()


def cmd_connect(args: argparse.Namespace) -> None:
    root = _root(args.path)
    if load_graph(root) is None:
        max_files = effective_max_files(DEFAULT_INDEX_MAX_FILES)
        files, _, _ = scan_project(root, max_files=max_files)
        save_graph(root, CodeGraph.build(files))
        print(f"indexed {root} (first run)")
    _wrote, message = connect_agent(args.agent, root)
    print(message)


def cmd_license_activate(args: argparse.Namespace) -> None:
    try:
        info = parse_and_verify_key(args.key)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    save_license(args.key, info)
    print("license activated")
    print(license_status_text())


def cmd_license_status(_args: argparse.Namespace) -> None:
    print(license_status_text())


def cmd_diagnose(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    trace = args.trace if args.trace is not None else sys.stdin.read()
    if not trace.strip():
        print("error: pass --trace '...' or pipe a stack trace on stdin", file=sys.stderr)
        sys.exit(2)
    report = diagnose_stack_trace(graph, trace)
    print(format_diagnosis(report))


def cmd_health(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    cycles = find_circular_imports(graph)
    dead = find_dead_exports(graph)
    print(f"# Codebase health — {root}\n")
    print(f"## Circular imports ({len(cycles)} cycle(s))")
    if not cycles:
        print("None found.")
    else:
        for i, cycle in enumerate(cycles[:20], 1):
            print(f"{i}. {' → '.join(cycle)} → {cycle[0]}")
    print(f"\n## Likely dead exports ({len(dead)} symbol(s))")
    if not dead:
        print("None found.")
    else:
        for item in dead[:50]:
            print(f"- {item['path']}:{item['line']} {item['signature']} [{item['kind']}]")
        if len(dead) > 50:
            print(f"... and {len(dead) - 50} more")


def cmd_audit(args: argparse.Namespace) -> None:
    root = _root(args.path)
    graph = _load_or_exit(root)
    hits = audit_symbol(graph, root, args.symbol)
    print(f"# Audit: {args.symbol!r} ({len(hits)} hit(s))\n")
    for h in hits:
        print(f"{h['path']}:{h['line']} [{h['kind']}] {h['detail']}")


def cmd_dashboard(args: argparse.Namespace) -> None:
    root = _root(args.path)
    if args.web:
        from vinemap.dashboard.server import serve_dashboard

        serve_dashboard(root, port=args.port)
        return
    graph = _load_or_exit(root)
    memory = SessionMemory(root)
    weights = memory.file_weights()
    stats = graph.stats()
    print(f"# Vinemap dashboard — {root}\n")
    print(f"tier:     {current_tier()}")
    print(f"index:    {stats['files']} files, {stats['symbols']} symbols")
    print(f"session:  {len(memory.events)} touches, {len(memory.decisions)} decisions")
    print(f"tokens:   ~{memory.total_tokens_saved():,} estimated via graph/inject")
    if weights:
        print("\n## Most touched files (this session)")
        for path, w in sorted(weights.items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {w:6.2f}  {path}")
    if memory.recent_decisions(20):
        print("\n## Recent decisions")
        for d in memory.recent_decisions(20):
            print(f"  - {d}")
    info = load_stored_license()
    if info and info.is_valid():
        print(f"\nlicense expires: {'never' if info.expires_at is None else info.expires_at}")
    print("\nTip: vinemap dashboard --web  for local UI")


def cmd_inject(args: argparse.Namespace) -> None:
    """Hook entrypoint: build and print injection pack for a user prompt."""
    query = args.query
    if query == "-":
        query = sys.stdin.read()
    query = extract_query_from_prompt(query)
    root = _root(args.path)
    pack, tokens = build_injection_pack(root, query, budget_tokens=args.budget)
    if pack:
        memory = SessionMemory(root)
        memory.record_tokens(tokens, "inject")
        memory.save()
        print(pack)
    sys.exit(0 if pack else 1)


def cmd_watch(args: argparse.Namespace) -> None:
    root = _root(args.path)
    _ensure_indexed(root, max_files=args.max_files)
    watch_project(root, interval=args.interval)


def cmd_setup(args: argparse.Namespace) -> None:
    """Full agent setup: hooks/rules + MCP (pre-injection enabled)."""
    root = _root(args.path)
    _ensure_indexed(root, max_files=args.max_files)
    setup = AGENT_SETUP.get(args.agent)
    if setup is None:
        # fallback to connect-only agents
        _wrote, message = connect_agent(args.agent, root)
        print(message)
        return
    _wrote, message = setup(root)
    print(message)


def cmd_clusters(args: argparse.Namespace) -> None:
    root = _root(args.path)
    clusters = detect_clusters(root)
    print(f"# Package clusters — {root}\n")
    for c in clusters:
        print(f"- {c.name} ({c.kind}) @ {c.root or '.'}")


def cmd_picker(path: str) -> None:
    """Interactive agent menu when user runs `vinemap .`"""
    root = _root(path)
    print("Vinemap — AI context infrastructure for your codebase\n")
    print(f"Project: {root}\n")
    labels = {
        "cursor": "Cursor (rules + MCP)",
        "claude": "Claude Code (hooks + MCP)",
        "gemini": "Gemini CLI (instructions + MCP)",
        "codex": "Codex CLI (project config + MCP snippet)",
        "copilot": "GitHub Copilot (instructions + VS Code MCP)",
        "opencode": "OpenCode (rules + MCP)",
    }
    agents = list(AGENT_SETUP.keys())
    for i, agent in enumerate(agents, 1):
        print(f"  {i}. {labels.get(agent, agent)}")
    print(f"  {len(agents) + 1}. quickstart wizard")
    print(f"  {len(agents) + 2}. index only")
    choice = input("\nChoose [1]: ").strip() or "1"
    if choice == str(len(agents) + 1):
        cmd_quickstart(argparse.Namespace(
            path=path, agent=None, query=None, budget=2000, max_files=DEFAULT_INDEX_MAX_FILES, yes=False,
        ))
        return
    if choice == str(len(agents) + 2):
        cmd_index(argparse.Namespace(path=path, max_files=DEFAULT_INDEX_MAX_FILES, store=None))
        return
    if choice.isdigit() and 1 <= int(choice) <= len(agents):
        agent = agents[int(choice) - 1]
    elif choice in AGENT_SETUP:
        agent = choice
    else:
        agent = "cursor"
    cmd_setup(argparse.Namespace(path=path, agent=agent, max_files=DEFAULT_INDEX_MAX_FILES))


def _cmd_agent_setup(agent: str):
    def _run(args: argparse.Namespace) -> None:
        args.agent = agent
        cmd_setup(args)

    return _run


def cmd_decide(args: argparse.Namespace) -> None:
    root = _root(args.path)
    memory = SessionMemory(root)
    memory.record_decision(args.text)
    memory.save()
    print("decision recorded")


def _ensure_indexed(root: str, max_files: Optional[int] = None) -> CodeGraph:
    graph = load_graph(root)
    if graph is not None:
        return graph
    cap = effective_max_files(max_files)
    files, _, _ = scan_project(root, max_files=cap)
    graph = CodeGraph.build(files)
    save_graph(root, graph)
    return graph


def _pick_agent_interactive() -> str:
    print("\nStep 2/3 — Connect your coding agent")
    labels = {
        "cursor": "Cursor",
        "claude": "Claude Code",
        "gemini": "Gemini CLI",
        "codex": "Codex CLI",
        "copilot": "GitHub Copilot",
        "opencode": "OpenCode",
    }
    for i, agent in enumerate(AGENTS, 1):
        print(f"  {i}. {labels[agent]}")
    while True:
        raw = input("Choose agent [1]: ").strip() or "1"
        if raw.isdigit() and 1 <= int(raw) <= len(AGENTS):
            return AGENTS[int(raw) - 1]
        if raw in AGENTS:
            return raw
        print(f"  enter 1–{len(AGENTS)} or one of: {', '.join(AGENTS)}")


def _agent_next_steps(agent: str) -> None:
    if agent == "cursor":
        print("  • Reload Cursor — Settings → MCP should list 'vinemap'")
    elif agent == "claude":
        print("  • Run `claude` in this project and approve the vinemap MCP server")
    elif agent == "gemini":
        print("  • Run `gemini` in this project to load the MCP config")
    elif agent == "codex":
        print("  • Run `codex` in this project or add MCP snippet to ~/.codex/config.toml")
    elif agent == "copilot":
        print("  • Reload VS Code — Copilot reads .github/copilot-instructions.md")
    elif agent == "opencode":
        print("  • OpenCode loads .opencode/rules and MCP from this project")
    else:
        print(f"  • Run `vinemap setup {agent}` if you need to reconfigure")


def cmd_quickstart(args: argparse.Namespace) -> None:
    root = _root(args.path)
    rel = "." if os.path.abspath(root) == os.getcwd() else root

    print("Vinemap quickstart")
    print(f"Project: {root}\n")

    print("Step 1/3 — Building code graph...")
    had_index = load_graph(root) is not None
    graph = _ensure_indexed(root, max_files=args.max_files)
    stats = graph.stats()
    if had_index:
        print(f"  using existing index — {stats['files']} files, {stats['symbols']} symbols")
    else:
        print(f"  indexed {stats['files']} files — {stats['symbols']} symbols")

    agent = args.agent
    if agent is None:
        if sys.stdin.isatty() and not args.yes:
            agent = _pick_agent_interactive()
        else:
            agent = "cursor"

    print(f"\nStep 2/3 — Configuring {agent}...")
    setup = AGENT_SETUP.get(agent)
    if setup is not None:
        _wrote, message = setup(root)
    else:
        _wrote, message = connect_agent(agent, root)
    print(message)

    query = args.query
    if not query:
        if sys.stdin.isatty() and not args.yes:
            print("\nStep 3/3 — Try a query about your codebase")
            query = input('Question (e.g. "where is auth handled"): ').strip()
        if not query:
            query = "main entry points and core modules"

    print(f"\nStep 3/3 — Query: {query!r}")
    memory = SessionMemory(root)
    ranked = rank_files(graph, query, k=5, memory=memory, project_root=root)
    if ranked:
        print("\nTop files:")
        for path, score in ranked:
            print(f"  {score:8.2f}  {path}")
    else:
        print("  no strong matches — try function, class, or file names from your project")

    pack, included = build_context_pack(
        root, graph, query, budget_tokens=args.budget, memory=memory
    )
    if pack:
        preview_limit = 900
        preview = pack if len(pack) <= preview_limit else pack[:preview_limit] + "\n...(truncated)"
        print(f"\nContext pack preview (~{estimate_tokens(pack)} tokens, {len(included)} files):")
        print(preview)
    elif ranked:
        print("\n(no pack generated — try a more specific query)")

    print("\n--- Done ---")
    print("Next steps:")
    _agent_next_steps(agent)
    print("  • Ask your agent to call graph_retrieve instead of grepping the repo")
    print(f"  • Re-index after big changes: vinemap index {rel}")
    maybe_prompt_feedback(context="quickstart")


def cmd_feedback(args: argparse.Namespace) -> None:
    message = args.message
    if not message and sys.stdin.isatty():
        print("Feedback for the Vinemap team (Ctrl+D or empty line to finish):")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        message = "\n".join(lines).strip()
    url = open_feedback(message or None, open_browser=not args.no_browser)
    print(f"Feedback: {url}")


def _teams_repo_id(root: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    return os.path.basename(os.path.abspath(root)).lower().replace(" ", "-")


def cmd_teams_connect(args: argparse.Namespace) -> None:
    require_teams("Teams shared graph")
    root = _root(args.path)
    repo_id = _teams_repo_id(root, args.repo_id)
    from vinemap.teams.config import save_teams_config

    path = save_teams_config(root, args.server_url, repo_id, token=args.token or "")
    print(f"wrote {path}")
    print(f"  server: {args.server_url}")
    print(f"  repo_id: {repo_id}")
    if args.verify:
        from vinemap.teams.client import TeamsClient

        client = TeamsClient(args.server_url, token=args.token or None)
        print("  health:", client.health())


def cmd_teams_push(args: argparse.Namespace) -> None:
    require_teams("Teams shared graph")
    root = _root(args.path)
    from vinemap.teams.config import get_client

    client, cfg = get_client(root)
    graph = _load_or_exit(root)
    repo_id = cfg.get("repo_id") or _teams_repo_id(root, None)
    name = args.name or repo_id
    result = client.push_graph(repo_id, name, graph.to_dict())
    print(f"pushed {repo_id} — {result.get('stats', {})}")


def cmd_teams_retrieve(args: argparse.Namespace) -> None:
    require_teams("cross-repo retrieval")
    root = args.path if args.path and os.path.isdir(args.path) else "."
    from vinemap.teams.config import get_client

    client, cfg = get_client(root)
    repo_id = cfg.get("repo_id") if args.local_only else None
    data = client.retrieve(args.query, k=args.k, repo_id=repo_id)
    for hit in data.get("results", []):
        print(f"{hit['score']:8.2f}  {hit['repo_id']}/{hit['path']}")
    if not data.get("results"):
        print("no matches")


def cmd_teams_decisions(args: argparse.Namespace) -> None:
    require_teams("shared decision memory")
    root = _root(args.path)
    from vinemap.teams.config import get_client

    client, cfg = get_client(root)
    if args.text:
        result = client.post_decision(args.text, repo_id=cfg.get("repo_id"))
        print(f"recorded decision #{result['id']} as {result['author']}")
        return
    for d in client.list_decisions(repo_id=cfg.get("repo_id"), limit=args.limit):
        repo = d.get("repo_id") or "org"
        print(f"- [{repo}] {d['author']}: {d['text']}")


def cmd_teams_sync(args: argparse.Namespace) -> None:
    """Push local graph and pull shared decisions into session memory."""
    require_teams("Teams sync")
    root = _root(args.path)
    cmd_teams_push(argparse.Namespace(path=root, name=None))
    from vinemap.teams.config import get_client

    client, cfg = get_client(root)
    memory = SessionMemory(root)
    for d in client.list_decisions(limit=20):
        memory.record_decision(f"[{d['author']}] {d['text']}")
    memory.save()
    print("synced graph + merged team decisions into local session memory")


def cmd_teams_status(args: argparse.Namespace) -> None:
    require_teams("Teams status")
    root = _root(args.path)
    from vinemap.teams.config import get_client, load_teams_config

    cfg = load_teams_config(root)
    if not cfg:
        print("not connected — run: vinemap teams connect <url>")
        sys.exit(1)
    client, _ = get_client(root)
    print(f"server:  {cfg['server_url']}")
    print(f"repo_id: {cfg.get('repo_id')}")
    print(f"health:  {client.health()}")
    print(f"repos:   {client.list_repos()}")


def main(argv: Optional[list] = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    # Bare `vinemap .` or `vinemap /path` → interactive picker
    if len(argv) == 1 and not argv[0].startswith("-") and os.path.isdir(os.path.abspath(argv[0])):
        cmd_picker(argv[0])
        return

    parser = argparse.ArgumentParser(
        prog="vinemap",
        description="Vinemap — local-first, graph-based context engine for AI coding agents",
    )
    parser.add_argument("--version", action="version", version=f"vinemap {__version__}")
    parser.add_argument(
        "--update",
        action="store_true",
        help="check PyPI for a newer version and exit",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p = sub.add_parser("index", help="build or refresh the code graph")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
    p.add_argument(
        "--store",
        choices=("auto", "json", "sqlite"),
        help="graph persistence backend (auto switches to sqlite at 2000+ files)",
    )
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
    p.add_argument("--coverage", action="store_true", help="include coverage confidence score")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("stats", help="index statistics")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("mcp", help="run the MCP server on stdio")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser("connect", help="configure an AI agent to use vinemap")
    p.add_argument("agent", choices=AGENTS)
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_connect)

    p = sub.add_parser("decide", help="record a session decision")
    p.add_argument("text")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("feedback", help="send feedback (opens GitHub issue)")
    p.add_argument("message", nargs="?", default="")
    p.add_argument("--no-browser", action="store_true", help="print URL only")
    p.set_defaults(func=cmd_feedback)

    p = sub.add_parser("quickstart", help="guided setup: index, connect agent, sample query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--agent", choices=AGENTS, help="agent to configure (default: cursor, or prompt)")
    p.add_argument("--query", help="sample question to rank files and preview a context pack")
    p.add_argument("--budget", type=int, default=2000, help="token budget for the preview pack")
    p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
    p.add_argument("-y", "--yes", action="store_true", help="non-interactive defaults (cursor, generic query)")
    p.set_defaults(func=cmd_quickstart)

    lic = sub.add_parser("license", help="Teams license management")
    lic_sub = lic.add_subparsers(dest="license_command", required=True)
    p = lic_sub.add_parser("activate", help="activate an offline license key")
    p.add_argument("key")
    p.set_defaults(func=cmd_license_activate)
    p = lic_sub.add_parser("status", help="show current tier and limits")
    p.set_defaults(func=cmd_license_status)

    p = sub.add_parser("diagnose", help="stack trace → root cause + blast radius")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--trace", help="stack trace text (default: read stdin)")
    p.set_defaults(func=cmd_diagnose)

    p = sub.add_parser("health", help="circular imports and dead exports")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("audit", help="exhaustive symbol search")
    p.add_argument("symbol")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("dashboard", help="session stats and token estimates")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--web", action="store_true", help="serve local web UI on localhost:7423")
    p.add_argument("--port", type=int, default=7423)
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("inject", help="build injection pack (for agent hooks)")
    p.add_argument("query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--budget", type=int, default=DEFAULT_BUDGET_TOKENS)
    p.set_defaults(func=cmd_inject)

    p = sub.add_parser("watch", help="re-index on file save (debounced)")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("setup", help="full agent setup with pre-injection hooks/rules")
    p.add_argument("agent", choices=tuple(AGENT_SETUP.keys()))
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
    p.set_defaults(func=cmd_setup)

    for agent in AGENT_SETUP:
        p = sub.add_parser(agent, help=f"setup {agent} (hooks/rules + MCP)")
        p.add_argument("path", nargs="?", default=".")
        p.add_argument("--max-files", type=int, default=DEFAULT_INDEX_MAX_FILES)
        p.set_defaults(func=_cmd_agent_setup(agent))

    p = sub.add_parser("clusters", help="list monorepo package boundaries")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_clusters)

    store = sub.add_parser("store", help="graph persistence backend")
    store_sub = store.add_subparsers(dest="store_command", required=True)
    p = store_sub.add_parser("migrate", help="migrate graph.json to SQLite")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_store_migrate)

    teams = sub.add_parser("teams", help="Teams shared graph (requires Teams license)")
    teams_sub = teams.add_subparsers(dest="teams_command", required=True)

    p = teams_sub.add_parser("connect", help="link project to Teams server")
    p.add_argument("server_url")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--repo-id", help="repo slug on server (default: directory name)")
    p.add_argument("--token", help="API bearer token")
    p.add_argument("--verify", action="store_true", help="ping server after save")
    p.set_defaults(func=cmd_teams_connect)

    p = teams_sub.add_parser("push", help="upload local graph to Teams server")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--name", help="display name on server")
    p.set_defaults(func=cmd_teams_push)

    p = teams_sub.add_parser("retrieve", help="cross-repo ranked file search")
    p.add_argument("query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("-k", type=int, default=10)
    p.add_argument("--local-only", action="store_true", help="search this repo only on server")
    p.set_defaults(func=cmd_teams_retrieve)

    p = teams_sub.add_parser("decisions", help="shared WHY memory with attribution")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--text", help="record a team decision")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_teams_decisions)

    p = teams_sub.add_parser("sync", help="push graph + pull team decisions locally")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_teams_sync)

    p = teams_sub.add_parser("status", help="Teams connection and server stats")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_teams_status)

    args = parser.parse_args(argv)
    if args.update:
        from vinemap.update_check import check_for_update

        latest = check_for_update()
        if latest:
            print(f"update available: vinemap {latest} (you have {__version__})")
            print("  pip install -U vinemap")
            sys.exit(1)
        print(f"vinemap {__version__} is up to date")
        sys.exit(0)
    if not args.command:
        parser.print_help()
        sys.exit(2)
    if args.command not in ("mcp", "inject"):
        from vinemap.update_check import maybe_notify_update

        maybe_notify_update()
    args.func(args)


if __name__ == "__main__":
    main()
