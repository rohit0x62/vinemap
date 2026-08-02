"""Codebase health: circular imports and dead exports."""

from typing import Dict, List, Set, Tuple

from vinemap.graph.model import CodeGraph


def find_circular_imports(graph: CodeGraph) -> List[List[str]]:
    """Return import cycles as lists of file paths (minimum cycle per SCC)."""
    cycles: List[List[str]] = []
    seen_cycles: Set[frozenset] = set()
    path = sorted(graph.files)
    index = {p: i for i, p in enumerate(path)}
    n = len(path)

    # Tarjan's algorithm for strongly connected components
    stack: List[int] = []
    on_stack: Set[int] = set()
    index_map: Dict[int, int] = {}
    lowlink: Dict[int, int] = {}
    counter = [0]
    sccs: List[List[int]] = []

    def strongconnect(v: int) -> None:
        index_map[v] = lowlink[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w_path in graph.import_edges.get(path[v], set()):
            if w_path not in index:
                continue
            w = index[w_path]
            if w not in index_map:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index_map[w])
        if lowlink[v] == index_map[v]:
            comp: List[int] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in range(n):
        if v not in index_map:
            strongconnect(v)

    for comp in sccs:
        if len(comp) < 2:
            continue
        cycle_paths = sorted(path[i] for i in comp)
        key = frozenset(cycle_paths)
        if key in seen_cycles:
            continue
        seen_cycles.add(key)
        cycles.append(cycle_paths)

    return sorted(cycles, key=len, reverse=True)


def find_dead_exports(graph: CodeGraph) -> List[dict]:
    """Symbols never referenced via imports/calls from other indexed files."""
    referenced: Set[Tuple[str, str]] = set()

    for path, pf in graph.files.items():
        for imp_target in graph.import_edges.get(path, set()):
            if imp_target in graph.files:
                referenced.add((imp_target, "*"))
        for sym in pf.symbols:
            for callee in sym.calls:
                for target_path in graph.symbol_index.get(callee.lower(), []):
                    referenced.add((target_path, callee.lower()))

    dead: List[dict] = []
    for path, pf in graph.files.items():
        for sym in pf.symbols:
            if sym.kind not in ("function", "class", "method"):
                continue
            name_key = sym.name.lower()
            if (path, name_key) in referenced or (path, "*") in referenced:
                continue
            # Entry points / dunder are not "dead"
            if sym.name in ("main",) or sym.name.startswith("__"):
                continue
            if len(graph.imported_by.get(path, set())) == 0 and sym.kind != "function":
                continue
            dead.append({
                "path": path,
                "symbol": sym.name,
                "kind": sym.kind,
                "line": sym.line_start,
                "signature": sym.signature or sym.name,
            })
    return sorted(dead, key=lambda d: (d["path"], d["line"]))
