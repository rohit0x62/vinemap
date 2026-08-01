"""Persistence for the code graph under <project>/.vinemap/."""

import json
import os
import tempfile
from typing import Optional

from vinemap import GRAPH_DIR
from vinemap.graph.model import CodeGraph

GRAPH_FILE = "graph.json"


def graph_dir(root: str) -> str:
    return os.path.join(root, GRAPH_DIR)


def atomic_write_json(path: str, data: object) -> None:
    """Write JSON via a temp file + rename so a crash never corrupts state."""
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_graph(root: str, graph: CodeGraph) -> str:
    d = graph_dir(root)
    os.makedirs(d, exist_ok=True)
    gitignore = os.path.join(d, ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w", encoding="utf-8") as f:
            f.write("*\n")
    path = os.path.join(d, GRAPH_FILE)
    atomic_write_json(path, graph.to_dict())
    return path


def _read_json(path: str) -> Optional[dict]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_graph(root: str) -> Optional[CodeGraph]:
    data = _read_json(os.path.join(graph_dir(root), GRAPH_FILE))
    if data is None:
        return None
    try:
        return CodeGraph.from_dict(data)
    except (KeyError, TypeError, AttributeError):
        # Corrupt or incompatible index: treat as absent, caller re-indexes.
        return None


def load_raw_files(root: str) -> dict:
    """Raw path -> ParsedFile dict map, used for incremental re-index caching."""
    data = _read_json(os.path.join(graph_dir(root), GRAPH_FILE))
    if data is None:
        return {}
    files = data.get("files", {})
    return files if isinstance(files, dict) else {}
