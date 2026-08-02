"""SQLite persistence for the Vinemap Teams shared graph server."""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional


class TeamsStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repos (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id TEXT,
                    author TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS seats (
                    email TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_decisions_repo ON decisions(repo_id);
                CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
                """
            )

    def audit(self, actor: str, action: str, detail: Optional[str] = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (actor, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (actor, action, detail, time.time()),
            )

    def upsert_repo(self, repo_id: str, name: str, graph: dict) -> None:
        body = json.dumps(graph)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO repos (id, name, graph_json, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, graph_json=excluded.graph_json,
                    updated_at=excluded.updated_at
                """,
                (repo_id, name, body, time.time()),
            )

    def get_repo(self, repo_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM repos WHERE id = ?", (repo_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "graph": json.loads(row["graph_json"]),
            "updated_at": row["updated_at"],
        }

    def list_repos(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, name, updated_at FROM repos ORDER BY name").fetchall()
        return [{"id": r["id"], "name": r["name"], "updated_at": r["updated_at"]} for r in rows]

    def all_graphs(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, name, graph_json FROM repos").fetchall()
        return [
            {"id": r["id"], "name": r["name"], "graph": json.loads(r["graph_json"])} for r in rows
        ]

    def add_decision(self, author: str, text: str, repo_id: Optional[str] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO decisions (repo_id, author, text, created_at) VALUES (?, ?, ?, ?)",
                (repo_id, author, text[:2000], time.time()),
            )
            return int(cur.lastrowid)

    def list_decisions(self, repo_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        with self._conn() as conn:
            if repo_id:
                rows = conn.execute(
                    "SELECT * FROM decisions WHERE repo_id = ? ORDER BY created_at DESC LIMIT ?",
                    (repo_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [
            {
                "id": r["id"],
                "repo_id": r["repo_id"],
                "author": r["author"],
                "text": r["text"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def add_seat(self, email: str, org_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO seats (email, org_id, active, created_at) VALUES (?, ?, 1, ?)
                ON CONFLICT(email) DO UPDATE SET org_id=excluded.org_id, active=1
                """,
                (email.lower(), org_id, time.time()),
            )

    def count_seats(self, org_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM seats WHERE org_id = ? AND active = 1", (org_id,)
            ).fetchone()
        return int(row["n"]) if row else 0

    def recent_audit(self, limit: int = 100) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "actor": r["actor"],
                "action": r["action"],
                "detail": r["detail"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def stats(self) -> dict:
        with self._conn() as conn:
            repos = conn.execute("SELECT COUNT(*) AS n FROM repos").fetchone()["n"]
            decisions = conn.execute("SELECT COUNT(*) AS n FROM decisions").fetchone()["n"]
            seats = conn.execute("SELECT COUNT(*) AS n FROM seats WHERE active = 1").fetchone()["n"]
        return {"repos": repos, "decisions": decisions, "seats": seats}
