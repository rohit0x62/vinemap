"""Cross-repo ranking over federated team graphs."""

from typing import List, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.rank.ranker import rank_files


def cross_repo_rank(
    repo_graphs: List[Tuple[str, CodeGraph]],
    query: str,
    k: int = 10,
) -> List[dict]:
    """Rank files across all repos; returns dicts with repo_id, path, score."""
    combined: List[Tuple[str, str, float]] = []
    per_repo_k = max(k, 5)
    for repo_id, graph in repo_graphs:
        for path, score in rank_files(graph, query, k=per_repo_k):
            combined.append((repo_id, path, score))
    combined.sort(key=lambda x: (-x[2], x[0], x[1]))
    seen = set()
    results: List[dict] = []
    for repo_id, path, score in combined:
        key = (repo_id, path)
        if key in seen:
            continue
        seen.add(key)
        results.append({"repo_id": repo_id, "path": path, "score": round(score, 2)})
        if len(results) >= k:
            break
    return results
