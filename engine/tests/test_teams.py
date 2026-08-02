"""Tests for Vinemap Teams server and client."""

import os
import sys
import time

import pytest

pytest.importorskip("fastapi")

# teams server lives at repo root
_TEAMS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "teams"))
if _TEAMS not in sys.path:
    sys.path.insert(0, _TEAMS)

from server.federated import cross_repo_rank
from server.store import TeamsStore
from vinemap.graph.model import CodeGraph
from vinemap.license import sign_license_payload
from vinemap.scanner.walker import scan_project

TEST_PRIV = "088ee4c67b4666c11fb02cea94d3356c628f2853c63c8b1f210dae9f0dc716f2"


@pytest.fixture
def store(tmp_path):
    return TeamsStore(str(tmp_path / "teams.db"))


def test_store_repo_roundtrip(store):
    graph = {"version": 1, "files": {}}
    store.upsert_repo("backend", "Backend API", graph)
    repo = store.get_repo("backend")
    assert repo["name"] == "Backend API"
    assert store.list_repos()[0]["id"] == "backend"


def test_decisions_with_attribution(store):
    store.add_decision("alice@co.com", "JWT validated in middleware", repo_id="api")
    store.add_decision("bob@co.com", "Use Redis for sessions", repo_id="api")
    decisions = store.list_decisions()
    assert len(decisions) == 2
    assert decisions[0]["author"] == "bob@co.com"


def test_cross_repo_rank(project, tmp_path):
    graph_a = CodeGraph.build(scan_project(project)[0])
    other = tmp_path / "other"
    other.mkdir()
    (other / "jwt.py").write_text("def validate_jwt(token): return True\n")
    graph_b = CodeGraph.build(scan_project(str(other))[0])
    results = cross_repo_rank(
        [("auth-service", graph_a), ("gateway", graph_b)],
        "password hashing",
        k=5,
    )
    assert results
    repos = {r["repo_id"] for r in results}
    assert "auth-service" in repos


def test_teams_api_index_and_retrieve(project, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    db = str(tmp_path / "data" / "teams.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    monkeypatch.setenv("VINEMAP_TEAMS_DATA_DIR", os.path.dirname(db))
    import server.main as main_mod

    monkeypatch.setattr(main_mod, "DB_PATH", db)
    monkeypatch.setattr(main_mod, "store", TeamsStore(db))

    client = TestClient(main_mod.app)
    graph = CodeGraph.build(scan_project(project)[0])
    r = client.post(
        "/v1/repos/demo/index",
        json={"name": "demo", "graph": graph.to_dict()},
        headers={"X-Vinemap-Actor": "tester"},
    )
    assert r.status_code == 200
    r = client.get(
        "/v1/retrieve?query=password+hashing&k=5",
        headers={"X-Vinemap-Actor": "tester"},
    )
    assert r.status_code == 200
    assert r.json()["results"]
