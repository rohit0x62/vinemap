"""Exhaustive audit: find every occurrence of a symbol across the graph."""

import os
import re
from typing import List

from vinemap.graph.model import CodeGraph


def audit_symbol(graph: CodeGraph, root: str, symbol: str) -> List[dict]:
    """Deep scan for a symbol name in the graph index and file contents."""
    needle = symbol.strip()
    if not needle:
        return []
    lower = needle.lower()
    hits: List[dict] = []

    # Graph index hits
    for path in graph.symbol_index.get(lower, []):
        pf = graph.files[path]
        for sym in pf.symbols:
            if sym.name.lower() == lower:
                hits.append({
                    "path": path,
                    "line": sym.line_start,
                    "kind": "definition",
                    "detail": sym.signature or sym.kind,
                })

    # Text search in indexed files (catches references the parser missed)
    word_re = re.compile(rf"\b{re.escape(needle)}\b")
    for path, pf in graph.files.items():
        full = os.path.join(root, path)
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if not word_re.search(line):
                        continue
                    if any(h["path"] == path and h["line"] == i for h in hits):
                        continue
                    hits.append({
                        "path": path,
                        "line": i,
                        "kind": "reference",
                        "detail": line.strip()[:120],
                    })
        except OSError:
            continue

    return sorted(hits, key=lambda h: (h["path"], h["line"], h["kind"]))
