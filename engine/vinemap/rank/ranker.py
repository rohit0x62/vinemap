"""Relevance ranking: which files matter for this question?

Scoring combines four signals:
  1. Lexical — query terms matching paths, module docs, symbol names, signatures.
  2. BM25 — dependency-free lexical scoring over the same text fields.
  3. Structural — import/call-graph expansion from strong hits.
  4. Session — files the agent already read/edited this session get a boost.

When ``project_root`` is provided, monorepo cluster names/prefixes also boost
matching files and same-cluster structural expansion is preferred.
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.memory.session import SessionMemory
from vinemap.rank.bm25 import bm25_scores
from vinemap.rank.embeddings import embedding_scores, embeddings_available
from vinemap.scanner.monorepo import cluster_for_path, detect_clusters

_WORD = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "what", "where", "when",
    "how", "why", "can", "does", "into", "are", "was", "will", "would", "should",
    "file", "files", "code", "function", "class", "add", "fix", "make", "use",
}
_GENERIC_PATH = {
    "server", "main", "model", "store", "client", "config", "utils", "helpers",
    "base", "common", "lib", "index", "types", "api",
}


def _term_variants(term: str) -> Set[str]:
    """Conservative stems for path/filename matching (not symbol names)."""
    out = {term}
    if len(term) > 5 and term.endswith("er"):
        out.add(term[:-2])
    if len(term) > 6 and term.endswith("ed"):
        out.add(term[:-1])
    return out


def _terms(query: str) -> List[str]:
    words = [w.lower() for w in _WORD.findall(query)]
    expanded: Set[str] = set()
    for w in words:
        expanded |= _term_variants(w)
        for part in re.split(r"_", w):
            if len(part) > 2:
                expanded |= _term_variants(part)
    return [w for w in expanded if len(w) > 2 and w not in _STOP]


def _path_stem(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[0].lower()


def _cluster_terms(clusters, path: str) -> Set[str]:
    c = cluster_for_path(clusters, path)
    if c is None:
        return set()
    tokens: Set[str] = set()
    for part in re.split(r"[/\-_]", c.name.lower()):
        if len(part) > 2:
            tokens.add(part)
    for part in c.root.split("/"):
        if len(part) > 2:
            tokens.add(part.lower())
    return tokens


def _clusters_for_query(
    clusters: List, terms: List[str]
) -> List[Tuple[object, int]]:
    """Return clusters whose name/root appears in query terms, with hit counts."""
    if not clusters:
        return []
    matched: List[Tuple[object, int]] = []
    for cluster in clusters:
        if not cluster.root:
            continue
        root_parts = [p.lower() for p in cluster.root.split("/") if len(p) > 2]
        name_parts = [p for p in re.split(r"[/\-_]", cluster.name.lower()) if len(p) > 2]
        hits = 0
        for t in terms:
            if t in root_parts or t in name_parts:
                hits += 1
            elif cluster.root and t in cluster.root.lower():
                hits += 1
        if hits > 0:
            matched.append((cluster, hits))
    matched.sort(key=lambda item: -item[1])
    return matched


def _apply_cluster_priority(
    scores: Dict[str, float],
    graph: CodeGraph,
    clusters: List,
    terms: List[str],
    term_hits: Dict[str, Set[str]],
) -> None:
    """Boost files in clusters explicitly mentioned by the query."""
    query_clusters = _clusters_for_query(clusters, terms)
    if not query_clusters:
        return

    primary, primary_hits = query_clusters[0]
    for path in graph.files:
        if cluster_for_path(clusters, path) != primary:
            continue
        scores[path] = scores.get(path, 0.0) + 8.0 + primary_hits * 4.0
        # Reward files whose path segments match query terms (e.g. teams/server/auth + oidc)
        segments = set(path.lower().replace(".", "/").split("/"))
        segment_hits = sum(1 for t in terms if t in segments)
        if segment_hits:
            scores[path] += segment_hits * 3.0

    # De-emphasize cross-cluster noise when query names a specific package
    if primary_hits >= 1:
        for path, hits in term_hits.items():
            if cluster_for_path(clusters, path) == primary:
                continue
            if hits and hits <= _GENERIC_PATH and all(h in _GENERIC_PATH for h in hits):
                scores[path] = scores.get(path, 0.0) * 0.25


def rank_files(
    graph: CodeGraph,
    query: str,
    k: int = 10,
    memory: Optional[SessionMemory] = None,
    project_root: Optional[str] = None,
) -> List[Tuple[str, float]]:
    """Return top-k (path, score) pairs for a natural-language query."""
    terms = _terms(query)
    scores: Dict[str, float] = {}
    term_hits: Dict[str, Set[str]] = {}
    clusters = detect_clusters(project_root) if project_root else []

    for path, pf in graph.files.items():
        s = 0.0
        hits: Set[str] = set()
        path_lower = path.lower()
        stem = _path_stem(path)
        module_doc = pf.module_docstring.lower()

        for t in terms:
            matched = False
            for v in _term_variants(t):
                if v == stem:
                    s += 6.0
                    matched = True
                elif stem.startswith(v) or v.startswith(stem):
                    s += 3.5
                    matched = True
                elif v in path_lower:
                    s += 2.0 if v not in _GENERIC_PATH else 0.8
                    matched = True
            if module_doc and t in module_doc:
                s += 4.5
                matched = True
            for sym in pf.symbols:
                name = sym.name.lower()
                doc = sym.docstring.lower()
                if t == name:
                    s += 5.0
                    matched = True
                elif t in name:
                    s += 2.0
                    matched = True
                elif t in sym.signature.lower():
                    s += 0.5
                    matched = True
                elif doc and t in doc:
                    s += 2.5
                    matched = True
            if matched:
                hits.add(t)

        if clusters:
            for ct in _cluster_terms(clusters, path):
                if ct in terms:
                    s += 4.0
                    hits.add(ct)

        if hits:
            if len(hits) >= 2:
                s *= 1.0 + 0.12 * (len(hits) - 1)
            if hits <= _GENERIC_PATH and all(h in _GENERIC_PATH for h in hits):
                s *= 0.35
            term_hits[path] = hits
            s += min(graph.degree(path), 10) * 0.1
            scores[path] = s

    for path, bm in bm25_scores(graph, query).items():
        scores[path] = scores.get(path, 0.0) + bm * 0.5

    _apply_cluster_priority(scores, graph, clusters, terms, term_hits)

    if embeddings_available() and project_root:
        for path, emb in embedding_scores(graph, query, project_root=project_root).items():
            scores[path] = scores.get(path, 0.0) + emb * 0.35

    seeds = sorted(scores.items(), key=lambda kv: -kv[1])[:5]
    for path, seed_score in seeds:
        src_cluster = cluster_for_path(clusters, path) if clusters else None
        related = (
            graph.import_edges.get(path, set())
            | graph.imported_by.get(path, set())
            | graph.call_edges.get(path, set())
            | graph.called_by.get(path, set())
        )
        for nb in related:
            boost = seed_score * 0.25
            if clusters and src_cluster is not None:
                nb_cluster = cluster_for_path(clusters, nb)
                if nb_cluster != src_cluster:
                    boost *= 0.55
            scores[nb] = scores.get(nb, 0.0) + boost

    if memory is not None:
        for path, weight in memory.file_weights().items():
            if path in graph.files:
                scores[path] = scores.get(path, 0.0) + weight * 2.0

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:k]
