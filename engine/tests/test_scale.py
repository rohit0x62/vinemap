"""Scale and lazy-loading tests."""

import os

import pytest

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, save_graph, set_store_backend
from vinemap.scanner.walker import scan_project


@pytest.mark.slow
def test_lazy_sqlite_loads_symbols_on_demand(tmp_path):
    pkg = tmp_path / "src"
    pkg.mkdir()
    for i in range(50):
        (pkg / f"m{i}.py").write_text(f"def f{i}(): return {i}\n")

    set_store_backend(str(tmp_path), "sqlite")
    files, _, _ = scan_project(str(tmp_path))
    graph = CodeGraph.build(files)
    save_graph(str(tmp_path), graph)

    lazy = load_graph(str(tmp_path), lazy=True)
    assert lazy is not None
    assert lazy.lazy
    assert lazy.stats()["symbols"] == 0

    path = next(iter(lazy.files))
    loaded = lazy.ensure_file(path)
    assert loaded is not None
    assert loaded.symbols


def test_stress_index_smoke(tmp_path):
    """100-file mini stress (fast enough for default CI)."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    for i in range(100):
        (pkg / f"mod_{i}.py").write_text(f"def handler_{i}(): pass\n")

    set_store_backend(str(tmp_path), "sqlite")
    files, _, _ = scan_project(str(tmp_path), max_files=200)
    graph = CodeGraph.build(files)
    save_graph(str(tmp_path), graph)
    loaded = load_graph(str(tmp_path), lazy=True)
    assert loaded is not None
    assert len(loaded.files) == 100
