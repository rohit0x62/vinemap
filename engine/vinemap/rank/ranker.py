"""Relevance ranking: which files matter for this question?

Scoring combines three signals, mirroring the dual-graph design:
  1. Lexical — query terms matching file paths, symbol names, signatures.
  2. Structural — import-graph expansion: files connected to strong lexical
     hits inherit part of their score (relevant code travels in clusters).
  3. Session — files the agent already read/edited this session get a boost.
"""

import re
from typing import Dict, List, Optional, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.memory.session import SessionMemory

_WORD = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "what", "where", "when",
    "how", "why", "can", "does", "into", "are", "was", "will", "would", "should",
    "file", "files", "code", "function", "class", "add", "fix", "make", "use",
}


def _terms(query: str) -> List[str]:
    words = [w.lower() for w in _WORD.findall(query)]
    # split camelCase / snake_case query words too
    expanded = set()
    for w in words:
        expanded.add(w)
        for part in re.split(r"_", w):
            if len(part) > 2:
                expanded.add(part)
    return [w for w in expanded if len(w) > 2 and w not in _STOP]


def rank_files(
    graph: CodeGraph,
    query: str,
    k: int = 10,
    memory: Optional[SessionMemory] = None,
) -> List[Tuple[str, float]]:
    """Return top-k (path, score) pairs for a natural-language query."""
    terms = _terms(query)
    scores: Dict[str, float] = {}

    for path, pf in graph.files.items():
        s = 0.0
        path_lower = path.lower()
        for t in terms:
            if t in path_lower:
                s += 3.0
        for sym in pf.symbols:
            name = sym.name.lower()
            doc = sym.docstring.lower()
            for t in terms:
                if t == name:
                    s += 5.0
                elif t in name:
                    s += 2.0
                elif t in sym.signature.lower():
                    s += 0.5
                elif doc and t in doc:
                    s += 1.0
        if s > 0:
            # small centrality prior: hub files are more likely to matter
            s += min(graph.degree(path), 10) * 0.1
            scores[path] = s

    # structural expansion from the strongest hits
    seeds = sorted(scores.items(), key=lambda kv: -kv[1])[:5]
    for path, s in seeds:
        for nb in graph.import_edges.get(path, set()) | graph.imported_by.get(path, set()):
            scores[nb] = scores.get(nb, 0.0) + s * 0.25

    # session memory boost
    if memory is not None:
        for path, weight in memory.file_weights().items():
            if path in graph.files:
                scores[path] = scores.get(path, 0.0) + weight * 2.0

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:k]
