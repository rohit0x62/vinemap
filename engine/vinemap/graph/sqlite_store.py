"""SQLite persistence for large code graphs (Pro/Teams scale).

Stores one row per file for incremental updates. Same public interface as
JSON store via vinemap.graph.store facade.
"""

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Iterator, Optional

from vinemap.graph.model import CodeGraph
from vinemap.scanner.parsers import ParsedFile

SCHEMA_VERSION = 1
GRAPH_DB = "graph.db"


@contextmanager
def _connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                line_count INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                module_docstring TEXT NOT NULL DEFAULT '',
                imports_json TEXT NOT NULL,
                symbols_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash);
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(files)")}
        if "module_docstring" not in cols:
            conn.execute(
                "ALTER TABLE files ADD COLUMN module_docstring TEXT NOT NULL DEFAULT ''"
            )


def save_graph_sqlite(db_path: str, graph: CodeGraph) -> str:
    init_db(db_path)
    with _connect(db_path) as conn:
        existing = {
            row["path"]: row["content_hash"]
            for row in conn.execute("SELECT path, content_hash FROM files")
        }
        current_paths = set(graph.files.keys())
        # Remove deleted files
        for path in set(existing.keys()) - current_paths:
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
        # Upsert files (skip unchanged hashes for fewer writes)
        for path, pf in graph.files.items():
            if existing.get(path) == pf.content_hash:
                continue
            conn.execute(
                """
                INSERT INTO files (path, language, line_count, content_hash, module_docstring, imports_json, symbols_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    language=excluded.language,
                    line_count=excluded.line_count,
                    content_hash=excluded.content_hash,
                    module_docstring=excluded.module_docstring,
                    imports_json=excluded.imports_json,
                    symbols_json=excluded.symbols_json
                """,
                (
                    path,
                    pf.language,
                    pf.line_count,
                    pf.content_hash,
                    pf.module_docstring,
                    json.dumps(pf.imports),
                    json.dumps([s.to_dict() for s in pf.symbols]),
                ),
            )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('file_count', ?)",
            (str(len(graph.files)),),
        )
    return db_path


def load_graph_sqlite(db_path: str) -> Optional[CodeGraph]:
    if not os.path.isfile(db_path):
        return None
    try:
        with _connect(db_path) as conn:
            rows = conn.execute("SELECT * FROM files").fetchall()
    except sqlite3.Error:
        return None
    if not rows:
        return None
    files = []
    for row in rows:
        pf = ParsedFile(
            path=row["path"],
            language=row["language"],
            line_count=row["line_count"],
            content_hash=row["content_hash"],
            module_docstring=row["module_docstring"] if "module_docstring" in row.keys() else "",
            imports=json.loads(row["imports_json"]),
        )
        from vinemap.scanner.parsers.base import Symbol

        pf.symbols = [Symbol.from_dict(s) for s in json.loads(row["symbols_json"])]
        files.append(pf)
    return CodeGraph.build(files)


def load_raw_files_sqlite(db_path: str) -> dict:
    """Path -> serialized ParsedFile dict for incremental re-index."""
    if not os.path.isfile(db_path):
        return {}
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(
                "SELECT path, language, line_count, content_hash, module_docstring, imports_json, symbols_json FROM files"
            ).fetchall()
    except sqlite3.Error:
        return {}
    out = {}
    for row in rows:
        out[row["path"]] = {
            "path": row["path"],
            "language": row["language"],
            "line_count": row["line_count"],
            "content_hash": row["content_hash"],
            "module_docstring": row["module_docstring"],
            "imports": json.loads(row["imports_json"]),
            "symbols": json.loads(row["symbols_json"]),
        }
    return out


def load_file_sqlite(db_path: str, path: str) -> Optional[ParsedFile]:
    """Lazy load a single file's ParsedFile from SQLite."""
    if not os.path.isfile(db_path):
        return None
    from vinemap.scanner.parsers.base import Symbol

    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
    if row is None:
        return None
    pf = ParsedFile(
        path=row["path"],
        language=row["language"],
        line_count=row["line_count"],
        content_hash=row["content_hash"],
        module_docstring=row["module_docstring"] if "module_docstring" in row.keys() else "",
        imports=json.loads(row["imports_json"]),
    )
    pf.symbols = [Symbol.from_dict(s) for s in json.loads(row["symbols_json"])]
    return pf


def load_graph_lazy_sqlite(db_path: str) -> Optional[CodeGraph]:
    """Load graph metadata only; symbols loaded on demand via CodeGraph.ensure_file."""
    if not os.path.isfile(db_path):
        return None
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT path, language, line_count, content_hash, module_docstring, imports_json
                FROM files
                """
            ).fetchall()
    except sqlite3.Error:
        return None
    if not rows:
        return None

    g = CodeGraph()
    g._lazy_db_path = db_path
    for row in rows:
        g.files[row["path"]] = ParsedFile(
            path=row["path"],
            language=row["language"],
            line_count=row["line_count"],
            content_hash=row["content_hash"],
            module_docstring=row["module_docstring"] if "module_docstring" in row.keys() else "",
            imports=json.loads(row["imports_json"]),
            symbols=[],
        )
    g._resolve_edges()
    return g


def migrate_json_to_sqlite(json_path: str, db_path: str) -> bool:
    """One-time migration from graph.json to graph.db."""
    if not os.path.isfile(json_path):
        return False
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        graph = CodeGraph.from_dict(data)
        save_graph_sqlite(db_path, graph)
        return True
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return False


def atomic_replace_db(src: str, dst: str) -> None:
    """Atomic rename for full rebuilds."""
    os.replace(src, dst)
