import json
import os
import subprocess
import sys

import pytest

from vinemap.connect import connect_agent
from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, load_raw_files, save_graph
from vinemap.mcp.server import McpServer
from vinemap.memory.session import SessionMemory
from vinemap.pack.packer import build_context_pack, estimate_tokens
from vinemap.rank.ranker import rank_files
from vinemap.scanner.parsers import get_parser
from vinemap.scanner.walker import scan_project


def _index(root):
    files, _, _ = scan_project(root)
    graph = CodeGraph.build(files)
    save_graph(root, graph)
    return graph


def test_python_parser_extracts_symbols_and_imports(project):
    parser = get_parser("auth.py")
    source = open(os.path.join(project, "app", "auth.py")).read()
    pf = parser.parse("app/auth.py", source)
    names = {s.name for s in pf.symbols}
    assert {"hash_password", "login", "SessionManager", "create_session"} <= names
    login_sym = next(s for s in pf.symbols if s.name == "login")
    assert "get_user" in login_sym.calls
    assert "app.db" in pf.imports
    sig = next(s for s in pf.symbols if s.name == "hash_password").signature
    assert sig.startswith("def hash_password(password: str")


def test_regex_parser_handles_typescript(project):
    parser = get_parser("web.ts")
    source = open(os.path.join(project, "web.ts")).read()
    pf = parser.parse("web.ts", source)
    names = {s.name for s in pf.symbols}
    assert "handleLogin" in names
    assert "ApiServer" in names
    assert "./app/auth" in pf.imports


def test_graph_builds_import_edges(project):
    graph = _index(project)
    assert graph.stats()["files"] == 3
    nb = graph.neighbors("app/auth.py")
    assert "app/db.py" in nb["imports"]
    assert "web.ts" in graph.neighbors("app/auth.py")["imported_by"]


def test_graph_roundtrips_through_store(project):
    _index(project)
    graph = load_graph(project)
    assert graph is not None
    assert "app/auth.py" in graph.files


def test_ranker_finds_relevant_files(project):
    graph = _index(project)
    ranked = rank_files(graph, "how does password hashing work in login?")
    paths = [p for p, _ in ranked]
    assert paths[0] == "app/auth.py"
    # structural expansion pulls in the imported db module
    assert "app/db.py" in paths


def test_ranker_matches_docstrings(project):
    graph = _index(project)
    # "salt" appears only in hash_password's docstring, not in any symbol name
    ranked = rank_files(graph, "salt handling")
    assert ranked and ranked[0][0] == "app/auth.py"


def test_session_memory_boosts_touched_files(project):
    graph = _index(project)
    memory = SessionMemory(project)
    memory.touch("web.ts", "edited")
    memory.save()
    ranked = rank_files(graph, "login handling", memory=memory)
    assert "web.ts" in [p for p, _ in ranked]


def test_packer_respects_budget_and_includes_code(project):
    graph = _index(project)
    pack, included = build_context_pack(project, graph, "password hashing", budget_tokens=2000)
    assert "app/auth.py" in included
    assert "<codebase_context>" in pack and "</codebase_context>" in pack
    assert "def hash_password" in pack  # inline code included
    assert estimate_tokens(pack) <= 2200  # small tolerance over budget


def test_mcp_server_initialize_and_tools(project):
    _index(project)
    server = McpServer(project)
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "vinemap"
    tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in tools["result"]["tools"]}
    assert {"graph_retrieve", "graph_read", "graph_neighbors", "graph_stats"} <= names
    call = server.handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "graph_retrieve", "arguments": {"query": "password hashing"}},
    })
    text = call["result"]["content"][0]["text"]
    assert "auth.py" in text


def test_mcp_stats_tool_reports_languages(project):
    _index(project)
    server = McpServer(project)
    call = server.handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "graph_stats", "arguments": {}},
    })
    stats = json.loads(call["result"]["content"][0]["text"])
    assert stats["files"] == 3
    assert "python" in stats["languages"]


def test_walker_skips_symlinks(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    secret = outside / "secret.py"
    secret.write_text("PASSWORD = 'hunter2'\n")
    os.symlink(str(secret), os.path.join(project, "linked.py"))
    os.symlink(str(outside), os.path.join(project, "linked_dir"))
    graph = _index(project)
    assert "linked.py" not in graph.files
    assert not any(p.startswith("linked_dir") for p in graph.files)


def test_packer_never_reads_outside_root(project, tmp_path_factory):
    graph = _index(project)
    outside = tmp_path_factory.mktemp("outside2")
    (outside / "evil.py").write_text("def hash_password():\n    return 'XYZZY_SENTINEL'\n" * 5)
    # simulate a tampered graph.json pointing outside the project
    pf = graph.files.pop("app/auth.py")
    pf.path = os.path.relpath(str(outside / "evil.py"), project).replace(os.sep, "/")
    graph.files[pf.path] = pf
    pack, _ = build_context_pack(project, graph, "password hashing")
    # the summary echoes graph metadata, but file CONTENTS outside the
    # project root must never be read from disk
    assert "XYZZY_SENTINEL" not in pack
    assert f"{pf.path}:" not in pack  # no inline code fence for the evil path


def test_mcp_rejects_bad_inputs(project):
    _index(project)
    server = McpServer(project)

    def call(name, arguments):
        return server.handle({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })

    r = call("graph_retrieve", {"query": ""})
    assert r["result"]["isError"] is True
    r = call("graph_retrieve", {"query": 42})
    assert r["result"]["isError"] is True
    r = call("graph_read", {"path": "../../etc/passwd"})
    assert "File not in index" in r["result"]["content"][0]["text"]
    r = call("__class__", {})
    assert "error" in r or r["result"].get("isError")
    # budget is clamped, not honored blindly
    r = call("graph_retrieve", {"query": "password hashing", "budget_tokens": 10 ** 9})
    assert r["result"].get("isError") is not True
    # malformed frames don't crash the dispatcher
    assert server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": []}) is not None


def test_corrupt_graph_file_treated_as_absent(project):
    _index(project)
    graph_file = os.path.join(project, ".vinemap", "graph.json")
    with open(graph_file, "w") as f:
        f.write("{not json")
    assert load_graph(project) is None
    assert load_raw_files(project) == {}


def test_connect_writes_and_merges_cursor_config(project):
    _index(project)
    cfg = os.path.join(project, ".cursor", "mcp.json")
    os.makedirs(os.path.dirname(cfg))
    with open(cfg, "w") as f:
        json.dump({"mcpServers": {"other": {"command": "x"}}}, f)
    wrote, _msg = connect_agent("cursor", project)
    assert wrote
    with open(cfg) as f:
        data = json.load(f)
    assert data["mcpServers"]["other"] == {"command": "x"}  # preserved
    assert data["mcpServers"]["vinemap"]["command"] == "vinemap"
    assert data["mcpServers"]["vinemap"]["args"][0] == "mcp"


def test_connect_claude_and_codex(project):
    wrote, _ = connect_agent("claude", project)
    assert wrote and os.path.isfile(os.path.join(project, ".mcp.json"))
    wrote, msg = connect_agent("codex", project)
    assert not wrote and "[mcp_servers.vinemap]" in msg


def test_cli_end_to_end(project):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    r = subprocess.run(
        [sys.executable, "-m", "vinemap.cli", "index", project],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "indexed 3 files" in r.stdout
    r = subprocess.run(
        [sys.executable, "-m", "vinemap.cli", "query", "password hashing", project],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "app/auth.py" in r.stdout


def test_cli_quickstart_non_interactive(project):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    r = subprocess.run(
        [
            sys.executable, "-m", "vinemap.cli", "quickstart", project,
            "--agent", "cursor", "--query", "password hashing", "-y",
        ],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "Step 1/3" in r.stdout
    assert "app/auth.py" in r.stdout
    assert "wrote" in r.stdout
    assert os.path.isfile(os.path.join(project, ".cursor", "mcp.json"))


def test_pro_commands_work_without_license(project):
    pytest.importorskip("cryptography")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    env["HOME"] = project  # no license file
    r = subprocess.run(
        [sys.executable, "-m", "vinemap.cli", "index", project],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    for cmd in (
        ["health", project],
        ["audit", "login", project],
    ):
        r = subprocess.run(
            [sys.executable, "-m", "vinemap.cli", *cmd],
            capture_output=True, text=True, env=env,
        )
        assert r.returncode == 0, (cmd, r.stderr)
