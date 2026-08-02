"""Project-scoped Teams server configuration."""

import json
import os
from typing import Optional

from vinemap import GRAPH_DIR
from vinemap.graph.store import atomic_write_json

TEAMS_CONFIG = "teams.json"


def teams_config_path(root: str) -> str:
    return os.path.join(root, GRAPH_DIR, TEAMS_CONFIG)


def load_teams_config(root: str) -> Optional[dict]:
    path = teams_config_path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def save_teams_config(root: str, server_url: str, repo_id: str, token: str = "") -> str:
    os.makedirs(os.path.join(root, GRAPH_DIR), exist_ok=True)
    path = teams_config_path(root)
    atomic_write_json(
        path,
        {
            "server_url": server_url.rstrip("/"),
            "repo_id": repo_id,
            "token": token,
        },
    )
    return path


def get_client(root: str):
    from vinemap.teams.client import TeamsClient

    cfg = load_teams_config(root)
    if cfg is None:
        raise SystemExit(
            "error: no Teams config — run `vinemap teams connect <server-url>` first"
        )
    return TeamsClient(
        cfg["server_url"],
        token=cfg.get("token") or None,
    ), cfg
