"""Dogfood retrieval quality tests on the monorepo-shaped workspace."""

import os

import pytest

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, save_graph
from vinemap.rank.ranker import rank_files
from vinemap.scanner.monorepo import detect_clusters
from vinemap.scanner.walker import scan_project

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(scope="module")
def repo_graph():
    files, _, _ = scan_project(REPO_ROOT, max_files=500)
    graph = CodeGraph.build(files)
    save_graph(REPO_ROOT, graph)
    return graph


def _top_paths(graph, query: str, k: int = 5):
    ranked = rank_files(graph, query, k=k, project_root=REPO_ROOT)
    return [path for path, _ in ranked]


def test_detects_teams_and_api_clusters():
    clusters = detect_clusters(REPO_ROOT)
    roots = {c.root for c in clusters}
    assert "teams" in roots
    assert "api" in roots
    assert "engine" in roots


def test_watch_query_finds_watch_module(repo_graph):
    paths = _top_paths(repo_graph, "file watcher debounced re-index")
    assert paths[0] == "engine/vinemap/watch.py"


def test_teams_oidc_query_prefers_teams_server(repo_graph):
    paths = _top_paths(repo_graph, "federated shared graph OIDC teams server", k=8)
    assert "teams/server/auth.py" in paths[:5]
    assert "teams/server/federated.py" in paths[:5]


def test_mcp_query_not_swamped_by_teams_server(repo_graph):
    paths = _top_paths(repo_graph, "MCP graph_retrieve stdio JSON-RPC")
    assert paths[0] == "engine/vinemap/mcp/server.py"
