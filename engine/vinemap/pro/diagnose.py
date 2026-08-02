"""Crash diagnosis: stack trace → root-cause candidates + blast radius."""

import re
from typing import Dict, List, Set, Tuple

from vinemap.graph.model import CodeGraph

_FRAME = re.compile(
    r'File\s+"([^"]+)"(?:,\s*line\s+(\d+))?|'
    r"^\s*File\s+\"([^\"]+)\",\s*line\s+(\d+)",
    re.MULTILINE,
)
_PATH_LINE = re.compile(r"([^\s:]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|php|kt|swift|cs|cpp|c|h)):(\d+)")


def _normalize_path(raw: str, graph: CodeGraph) -> str:
    raw = raw.replace("\\", "/")
    if raw in graph.files:
        return raw
    # Match by suffix (trace may use absolute paths)
    for path in graph.files:
        if raw.endswith(path) or path.endswith(raw.lstrip("./")):
            return path
    base = raw.rsplit("/", 1)[-1]
    matches = [p for p in graph.files if p.endswith("/" + base) or p == base]
    if len(matches) == 1:
        return matches[0]
    return raw


def _parse_frames(trace: str, graph: CodeGraph) -> List[Tuple[str, int]]:
    frames: List[Tuple[str, int]] = []
    seen: Set[Tuple[str, int]] = set()

    for m in _FRAME.finditer(trace):
        path = m.group(1) or m.group(3)
        line_s = m.group(2) or m.group(4)
        if not path:
            continue
        line = int(line_s) if line_s else 0
        norm = _normalize_path(path, graph)
        key = (norm, line)
        if key not in seen:
            seen.add(key)
            frames.append(key)

    for m in _PATH_LINE.finditer(trace):
        norm = _normalize_path(m.group(1), graph)
        key = (norm, int(m.group(2)))
        if key not in seen:
            seen.add(key)
            frames.append(key)

    return frames


def _blast_radius(graph: CodeGraph, seed_paths: Set[str], depth: int = 3) -> Set[str]:
    frontier = set(seed_paths)
    visited: Set[str] = set()
    for _ in range(depth):
        next_frontier: Set[str] = set()
        for path in frontier:
            if path in visited or path not in graph.files:
                continue
            visited.add(path)
            next_frontier |= graph.import_edges.get(path, set())
            next_frontier |= graph.imported_by.get(path, set())
            next_frontier |= graph.call_edges.get(path, set())
            next_frontier |= graph.called_by.get(path, set())
        frontier = next_frontier - visited
    return visited


def diagnose_stack_trace(graph: CodeGraph, trace: str, blast_depth: int = 3) -> dict:
    """Return structured crash diagnosis from a stack trace string."""
    frames = _parse_frames(trace, graph)
    in_index = [(p, ln) for p, ln in frames if p in graph.files]

    candidates: List[dict] = []
    for path, line in in_index[:8]:
        pf = graph.files[path]
        sym = None
        for s in pf.symbols:
            if s.line_start <= line <= s.line_end:
                sym = s
                break
        nb = graph.neighbors(path)
        candidates.append({
            "path": path,
            "line": line,
            "symbol": sym.name if sym else None,
            "signature": sym.signature if sym else None,
            "imports": nb["imports"][:6],
            "imported_by": nb["imported_by"][:6],
        })

    seed = {p for p, _ in in_index}
    blast = sorted(_blast_radius(graph, seed, depth=blast_depth) - seed)

    return {
        "frames_in_index": len(in_index),
        "frames_total": len(frames),
        "root_candidates": candidates,
        "blast_radius": blast,
        "blast_radius_count": len(blast),
    }


def format_diagnosis(report: dict) -> str:
    lines = ["# Crash diagnosis", ""]
    if not report["root_candidates"]:
        lines.append("No stack frames matched the indexed graph.")
        lines.append("Re-run `vinemap index` or paste a trace with project-relative paths.")
        return "\n".join(lines)

    lines.append(f"Matched {report['frames_in_index']} frame(s) in the index.\n")
    lines.append("## Root-cause candidates")
    for i, c in enumerate(report["root_candidates"], 1):
        loc = f"{c['path']}:{c['line']}"
        sym = f" ({c['symbol']})" if c["symbol"] else ""
        lines.append(f"{i}. **{loc}**{sym}")
        if c["signature"]:
            lines.append(f"   `{c['signature']}`")
        if c["imports"]:
            lines.append(f"   imports: {', '.join(c['imports'])}")
        if c["imported_by"]:
            lines.append(f"   imported by: {', '.join(c['imported_by'])}")
        lines.append("")

    lines.append(f"## Blast radius ({report['blast_radius_count']} files)")
    for path in report["blast_radius"][:25]:
        lines.append(f"- {path}")
    if report["blast_radius_count"] > 25:
        lines.append(f"- ... and {report['blast_radius_count'] - 25} more")
    return "\n".join(lines)
