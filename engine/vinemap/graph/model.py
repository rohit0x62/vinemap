"""The code graph: files and symbols as nodes, imports/calls/contains as edges."""

import posixpath
from collections import defaultdict
from typing import Dict, List, Optional, Set

from vinemap.scanner.parsers import ParsedFile


class CodeGraph:
    """In-memory dual graph of a project.

    Structural layer: file nodes, symbol nodes, import edges, call edges.
    A separate session layer (vinemap.memory) records what the agent touched.
    """

    def __init__(self) -> None:
        self.files: Dict[str, ParsedFile] = {}
        self.import_edges: Dict[str, Set[str]] = defaultdict(set)  # file -> files it imports
        self.imported_by: Dict[str, Set[str]] = defaultdict(set)   # reverse edges
        self.symbol_index: Dict[str, List[str]] = defaultdict(list)  # symbol name -> [paths]

    # -- construction ------------------------------------------------------

    @staticmethod
    def build(parsed_files: List[ParsedFile]) -> "CodeGraph":
        g = CodeGraph()
        for pf in parsed_files:
            g.files[pf.path] = pf
        g._resolve_edges()
        return g

    def _resolve_edges(self) -> None:
        self.import_edges.clear()
        self.imported_by.clear()
        self.symbol_index.clear()

        # Index: module-ish keys -> path. e.g. "src/app/db.py" is reachable as
        # "db", "app.db", "src.app.db", "src/app/db", "./db" (relative import).
        module_index: Dict[str, str] = {}
        for path in self.files:
            no_ext = path.rsplit(".", 1)[0]
            parts = no_ext.split("/")
            for i in range(len(parts)):
                dotted = ".".join(parts[i:])
                slashed = "/".join(parts[i:])
                module_index.setdefault(dotted, path)
                module_index.setdefault(slashed, path)

        for path, pf in self.files.items():
            base_dir = posixpath.dirname(path)
            for imp in pf.imports:
                target = self._resolve_import(imp, base_dir, module_index)
                if target and target != path:
                    self.import_edges[path].add(target)
                    self.imported_by[target].add(path)
            for sym in pf.symbols:
                self.symbol_index[sym.name.lower()].append(path)

    def _resolve_import(
        self, spec: str, base_dir: str, module_index: Dict[str, str]
    ) -> Optional[str]:
        spec = spec.strip()
        # Relative path imports (JS/TS style): ./foo, ../bar/baz
        if spec.startswith("."):
            joined = posixpath.normpath(posixpath.join(base_dir, spec.lstrip(".") or "."))
            candidates = [joined, spec.lstrip("./")]
            for cand in candidates:
                for path in self.files:
                    no_ext = path.rsplit(".", 1)[0]
                    if no_ext == cand or no_ext.endswith("/" + cand) or no_ext == cand + "/index":
                        return path
            return None
        # Dotted or slashed module imports
        key = spec.replace("::", ".")
        for candidate in (key, key.replace("/", "."), key.replace(".", "/")):
            if candidate in module_index:
                return module_index[candidate]
        # Try trimming trailing segments (import of a symbol inside a module)
        parts = key.replace("/", ".").split(".")
        while len(parts) > 1:
            parts.pop()
            trimmed = ".".join(parts)
            if trimmed in module_index:
                return module_index[trimmed]
        return None

    # -- queries -----------------------------------------------------------

    def neighbors(self, path: str) -> Dict[str, List[str]]:
        return {
            "imports": sorted(self.import_edges.get(path, set())),
            "imported_by": sorted(self.imported_by.get(path, set())),
        }

    def degree(self, path: str) -> int:
        return len(self.import_edges.get(path, ())) + len(self.imported_by.get(path, ()))

    def stats(self) -> dict:
        n_symbols = sum(len(pf.symbols) for pf in self.files.values())
        n_edges = sum(len(v) for v in self.import_edges.values())
        langs: Dict[str, int] = defaultdict(int)
        for pf in self.files.values():
            langs[pf.language] += 1
        return {
            "files": len(self.files),
            "symbols": n_symbols,
            "import_edges": n_edges,
            "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        }

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        return {"version": 1, "files": {p: pf.to_dict() for p, pf in self.files.items()}}

    @staticmethod
    def from_dict(d: dict) -> "CodeGraph":
        files = [ParsedFile.from_dict(v) for v in d.get("files", {}).values()]
        return CodeGraph.build(files)
