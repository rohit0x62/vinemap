"""Coverage score: how completely a context pack covers a query's blast radius."""

from typing import List, Set, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.rank.ranker import rank_files


def _relevant_universe(graph: CodeGraph, query: str, k: int = 12) -> Set[str]:
    ranked = rank_files(graph, query, k=k)
    universe: Set[str] = {p for p, _ in ranked}
    for path, _ in ranked[:5]:
        universe |= graph.import_edges.get(path, set())
        universe |= graph.imported_by.get(path, set())
    return universe


def coverage_score(
    graph: CodeGraph,
    query: str,
    included_paths: List[str],
    k: int = 12,
) -> Tuple[float, int, int]:
    """Return (score 0–100, included_count, universe_count)."""
    universe = _relevant_universe(graph, query, k=k)
    if not universe:
        return 0.0, 0, 0
    included = set(included_paths) & universe
    score = 100.0 * len(included) / len(universe)
    return round(score, 1), len(included), len(universe)
