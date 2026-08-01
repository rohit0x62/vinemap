"""Session memory: the live action layer of the dual graph.

Tracks which files were retrieved/read/edited and which decisions were made,
so follow-up questions route straight to previously relevant context and new
sessions start warm instead of cold.
"""

import json
import os
import time
from typing import Dict, List

from vinemap import GRAPH_DIR
from vinemap.graph.store import atomic_write_json

MEMORY_FILE = "session.json"

_ACTION_WEIGHTS = {"retrieved": 0.5, "read": 1.0, "edited": 2.0}
_HALF_LIFE_SECONDS = 6 * 3600  # touches decay with a 6h half-life


class SessionMemory:
    def __init__(self, root: str):
        self.root = root
        self.path = os.path.join(root, GRAPH_DIR, MEMORY_FILE)
        self.events: List[dict] = []
        self.decisions: List[dict] = []
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                self.events = data.get("events", [])
                self.decisions = data.get("decisions", [])
            except (json.JSONDecodeError, OSError):
                self.events, self.decisions = [], []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        atomic_write_json(
            self.path,
            {"events": self.events[-500:], "decisions": self.decisions[-100:]},
        )

    def touch(self, path: str, action: str = "read") -> None:
        self.events.append({"path": path, "action": action, "ts": time.time()})

    def record_decision(self, text: str) -> None:
        self.decisions.append({"text": text[:500], "ts": time.time()})

    def file_weights(self) -> Dict[str, float]:
        """Time-decayed weight per file, higher = more recently/strongly touched."""
        now = time.time()
        weights: Dict[str, float] = {}
        for ev in self.events:
            age = max(now - ev.get("ts", now), 0)
            decay = 0.5 ** (age / _HALF_LIFE_SECONDS)
            w = _ACTION_WEIGHTS.get(ev.get("action", "read"), 1.0) * decay
            weights[ev["path"]] = weights.get(ev["path"], 0.0) + w
        return weights

    def recent_decisions(self, n: int = 5) -> List[str]:
        return [d["text"] for d in self.decisions[-n:]]
