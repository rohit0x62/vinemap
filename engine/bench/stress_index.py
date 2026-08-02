#!/usr/bin/env python3
"""Scale benchmark: index + query on synthetic projects.

Usage:
  python bench/stress_index.py --files 1000          # CI-scale smoke
  python bench/stress_index.py --files 100000        # manual large-scale run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, save_graph, set_store_backend
from vinemap.rank.ranker import rank_files
from vinemap.scanner.walker import scan_project


def _write_synthetic_tree(root: str, n_files: int) -> None:
    pkg = os.path.join(root, "src", "app")
    os.makedirs(pkg, exist_ok=True)
    for i in range(n_files):
        path = os.path.join(pkg, f"mod_{i:05d}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f'"""Module {i} for scale testing."""\n\n'
                f"def handler_{i}(value: int) -> int:\n"
                f"    return value + {i}\n\n"
                f"class Service{i}:\n"
                f"    def run(self) -> None:\n"
                f"        handler_{i}(1)\n"
            )


def run_benchmark(n_files: int, lazy_load: bool) -> dict:
    tmp = tempfile.mkdtemp(prefix="vinemap-bench-")
    try:
        _write_synthetic_tree(tmp, n_files)
        set_store_backend(tmp, "sqlite")

        t0 = time.time()
        files, n_parsed, n_cached = scan_project(tmp, max_files=n_files + 10)
        graph = CodeGraph.build(files)
        save_graph(tmp, graph)
        index_s = time.time() - t0

        t1 = time.time()
        loaded = load_graph(tmp, lazy=lazy_load)
        load_s = time.time() - t1

        t2 = time.time()
        ranked = rank_files(loaded, "handler service module", k=10, project_root=tmp)
        query_s = time.time() - t2

        lazy_s = 0.0
        if lazy_load and loaded and loaded.lazy:
            t3 = time.time()
            for path, _ in ranked[:3]:
                loaded.ensure_file(path)
            lazy_s = time.time() - t3

        return {
            "files": n_files,
            "parsed": n_parsed,
            "cached": n_cached,
            "index_s": index_s,
            "load_s": load_s,
            "query_s": query_s,
            "lazy_read_s": lazy_s,
            "lazy": lazy_load,
            "top": ranked[0][0] if ranked else None,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Vinemap index/query stress benchmark")
    parser.add_argument("--files", type=int, default=1000)
    parser.add_argument("--lazy", action="store_true", help="Use lazy SQLite graph load")
    args = parser.parse_args()

    result = run_benchmark(args.files, lazy_load=args.lazy)
    print(f"files={result['files']} lazy={result['lazy']}")
    print(f"  index:  {result['index_s']:.2f}s ({result['parsed']} parsed, {result['cached']} cached)")
    print(f"  load:   {result['load_s']:.3f}s")
    print(f"  query:  {result['query_s']:.3f}s  top={result['top']!r}")
    if result["lazy"]:
        print(f"  lazy read (top 3): {result['lazy_read_s']:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
