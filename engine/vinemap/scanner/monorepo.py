"""Monorepo package boundary detection for cluster-aware retrieval."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PackageCluster:
    name: str
    root: str  # relative path prefix
    kind: str  # python | node | go | rust | other
    meta: dict = field(default_factory=dict)


def detect_clusters(project_root: str) -> List[PackageCluster]:
    """Find package boundaries from manifest files."""
    root = os.path.abspath(project_root)
    clusters: List[PackageCluster] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "venv", ".venv")]
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        prefix = "" if rel == "." else rel

        if "pyproject.toml" in filenames or "setup.py" in filenames:
            clusters.append(PackageCluster(name=prefix or "python-root", root=prefix, kind="python"))
        if "package.json" in filenames:
            name = prefix or "node-root"
            try:
                with open(os.path.join(dirpath, "package.json"), encoding="utf-8") as f:
                    pkg = json.load(f)
                name = pkg.get("name", name)
            except (json.JSONDecodeError, OSError):
                pass
            clusters.append(PackageCluster(name=name, root=prefix, kind="node"))
        if "go.mod" in filenames:
            clusters.append(PackageCluster(name=prefix or "go-root", root=prefix, kind="go"))
        if "Cargo.toml" in filenames:
            clusters.append(PackageCluster(name=prefix or "rust-root", root=prefix, kind="rust"))
        if "requirements.txt" in filenames and "pyproject.toml" not in filenames:
            name = os.path.basename(prefix) if prefix else "python-service"
            clusters.append(PackageCluster(name=name, root=prefix, kind="python"))

    if not clusters:
        clusters.append(PackageCluster(name="root", root="", kind="other"))
    return clusters


def cluster_for_path(clusters: List[PackageCluster], path: str) -> Optional[PackageCluster]:
    """Return the innermost cluster containing path."""
    best: Optional[PackageCluster] = None
    best_len = -1
    for c in clusters:
        if c.root == "" or path == c.root or path.startswith(c.root + "/"):
            if len(c.root) >= best_len:
                best = c
                best_len = len(c.root)
    return best


def cluster_map(clusters: List[PackageCluster]) -> Dict[str, str]:
    """Map cluster root prefix -> cluster name."""
    return {c.root: c.name for c in clusters}
