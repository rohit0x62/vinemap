import os

import pytest

from vinemap.graph.model import CodeGraph
from vinemap.graph.sqlite_store import (
    load_file_sqlite,
    load_graph_sqlite,
    load_raw_files_sqlite,
    migrate_json_to_sqlite,
    save_graph_sqlite,
)
from vinemap.graph.store import (
    GRAPH_DB,
    GRAPH_FILE,
    get_store_backend,
    load_graph,
    load_raw_files,
    migrate_to_sqlite,
    save_graph,
    set_store_backend,
)
from vinemap.scanner.parsers.base import ParsedFile, Symbol
from vinemap.scanner.walker import content_hash, scan_project


def _sample_graph() -> CodeGraph:
    pf = ParsedFile(
        path="app/auth.py",
        language="python",
        line_count=10,
        content_hash=content_hash("def login(): pass"),
        imports=["app.db"],
        symbols=[
            Symbol(
                name="login",
                kind="function",
                line_start=1,
                line_end=3,
                signature="def login():",
                calls=["get_user"],
            )
        ],
    )
    return CodeGraph.build([pf])


def test_sqlite_save_load_roundtrip(tmp_path):
    db = str(tmp_path / "graph.db")
    graph = _sample_graph()
    save_graph_sqlite(db, graph)
    loaded = load_graph_sqlite(db)
    assert loaded is not None
    assert "app/auth.py" in loaded.files
    assert loaded.files["app/auth.py"].symbols[0].name == "login"
    assert loaded.files["app/auth.py"].imports == ["app.db"]


def test_sqlite_incremental_skips_unchanged(tmp_path):
    db = str(tmp_path / "graph.db")
    graph = _sample_graph()
    save_graph_sqlite(db, graph)

    import sqlite3

    with sqlite3.connect(db) as conn:
        before = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    save_graph_sqlite(db, graph)

    with sqlite3.connect(db) as conn:
        after = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    assert before == after == 1


def test_sqlite_load_raw_and_single_file(tmp_path):
    db = str(tmp_path / "graph.db")
    graph = _sample_graph()
    save_graph_sqlite(db, graph)

    raw = load_raw_files_sqlite(db)
    assert "app/auth.py" in raw
    assert raw["app/auth.py"]["content_hash"] == graph.files["app/auth.py"].content_hash

    pf = load_file_sqlite(db, "app/auth.py")
    assert pf is not None
    assert pf.symbols[0].calls == ["get_user"]
    assert load_file_sqlite(db, "missing.py") is None


def test_store_facade_sqlite_backend(project):
    set_store_backend(project, "sqlite")
    assert get_store_backend(project) == "sqlite"

    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    path = save_graph(project, graph)
    assert path.endswith(GRAPH_DB)
    assert load_graph(project) is not None
    assert "app/auth.py" in load_raw_files(project)


def test_migrate_json_to_sqlite(project):
    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    set_store_backend(project, "json")
    save_graph(project, graph)

    json_path = os.path.join(project, ".vinemap", GRAPH_FILE)
    db_path = os.path.join(project, ".vinemap", GRAPH_DB)
    assert os.path.isfile(json_path)

    assert migrate_json_to_sqlite(json_path, db_path) is True
    loaded = load_graph_sqlite(db_path)
    assert loaded is not None
    assert loaded.stats()["files"] == graph.stats()["files"]


def test_migrate_to_sqlite_cli_path(project):
    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    set_store_backend(project, "json")
    save_graph(project, graph)

    db = migrate_to_sqlite(project)
    assert db is not None
    assert db.endswith(GRAPH_DB)
    assert get_store_backend(project) == "sqlite"
    assert load_graph(project) is not None


def test_auto_switches_to_sqlite_at_threshold(tmp_path):
    set_store_backend(str(tmp_path), "auto")
    files = []
    for i in range(2000):
        pf = ParsedFile(
            path=f"src/f{i}.py",
            language="python",
            line_count=1,
            content_hash=f"hash{i}",
        )
        files.append(pf)
    graph = CodeGraph.build(files)
    path = save_graph(str(tmp_path), graph)
    assert path.endswith(GRAPH_DB)
