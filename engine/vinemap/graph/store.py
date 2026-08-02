"""Persistence for the code graph under <project>/.vinemap/."""

import json
import os
import tempfile
from typing import Literal, Optional

from vinemap import GRAPH_DIR
from vinemap.graph.model import CodeGraph

GRAPH_FILE = "graph.json"
GRAPH_DB = "graph.db"
STORE_CONFIG = "store.json"
SQLITE_AUTO_THRESHOLD = 2000

StoreBackend = Literal["auto", "json", "sqlite"]


def graph_dir(root: str) -> str:
    return os.path.join(root, GRAPH_DIR)


def _config_path(root: str) -> str:
    return os.path.join(graph_dir(root), STORE_CONFIG)


def get_store_backend(root: str) -> StoreBackend:
    path = _config_path(root)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            backend = data.get("backend", "auto")
            if backend in ("auto", "json", "sqlite"):
                return backend
        except (json.JSONDecodeError, OSError):
            pass
    return "auto"


def set_store_backend(root: str, backend: StoreBackend) -> None:
    os.makedirs(graph_dir(root), exist_ok=True)
    atomic_write_json(_config_path(root), {"backend": backend})


def _resolve_backend(root: str, file_count: int) -> Literal["json", "sqlite"]:
    backend = get_store_backend(root)
    if backend == "sqlite":
        return "sqlite"
    if backend == "json":
        return "json"
    # auto
    if file_count >= SQLITE_AUTO_THRESHOLD:
        return "sqlite"
    if os.path.isfile(os.path.join(graph_dir(root), GRAPH_DB)):
        return "sqlite"
    return "json"


def _ensure_gitignore(root: str) -> None:
    d = graph_dir(root)
    os.makedirs(d, exist_ok=True)
    gitignore = os.path.join(d, ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w", encoding="utf-8") as f:
            f.write("*\n")


def atomic_write_json(path: str, data: object) -> None:
    """Write JSON via a temp file + rename so a crash never corrupts state."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
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
    _ensure_gitignore(root)
    backend = _resolve_backend(root, len(graph.files))
    if backend == "sqlite":
        from vinemap.graph.sqlite_store import save_graph_sqlite

        db_path = os.path.join(graph_dir(root), GRAPH_DB)
        return save_graph_sqlite(db_path, graph)
    path = os.path.join(graph_dir(root), GRAPH_FILE)
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


def load_graph(root: str, lazy: bool = False) -> Optional[CodeGraph]:
    d = graph_dir(root)
    db_path = os.path.join(d, GRAPH_DB)
    json_path = os.path.join(d, GRAPH_FILE)

    if os.path.isfile(db_path):
        from vinemap.graph.sqlite_store import load_graph_lazy_sqlite, load_graph_sqlite

        if lazy:
            graph = load_graph_lazy_sqlite(db_path)
        else:
            graph = load_graph_sqlite(db_path)
        if graph is not None:
            return graph

    data = _read_json(json_path)
    if data is None:
        return None
    try:
        return CodeGraph.from_dict(data)
    except (KeyError, TypeError, AttributeError):
        return None


def load_raw_files(root: str) -> dict:
    """Raw path -> ParsedFile dict map, used for incremental re-index caching."""
    d = graph_dir(root)
    db_path = os.path.join(d, GRAPH_DB)
    if os.path.isfile(db_path):
        from vinemap.graph.sqlite_store import load_raw_files_sqlite

        return load_raw_files_sqlite(db_path)

    data = _read_json(os.path.join(d, GRAPH_FILE))
    if data is None:
        return {}
    files = data.get("files", {})
    return files if isinstance(files, dict) else {}


def migrate_to_sqlite(root: str) -> Optional[str]:
    """Migrate graph.json → graph.db. Returns db path on success."""
    from vinemap.graph.sqlite_store import migrate_json_to_sqlite

    d = graph_dir(root)
    json_path = os.path.join(d, GRAPH_FILE)
    db_path = os.path.join(d, GRAPH_DB)
    if migrate_json_to_sqlite(json_path, db_path):
        set_store_backend(root, "sqlite")
        return db_path
    return None
