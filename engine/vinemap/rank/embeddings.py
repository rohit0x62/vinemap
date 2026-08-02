"""Optional semantic embedding signal for file ranking.

Install: pip install vinemap[embeddings]

Uses sentence-transformers (all-MiniLM-L6-v2) locally. Embeddings are cached
under <project>/.vinemap/emb_cache.json keyed by content hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List, Optional

from vinemap import GRAPH_DIR
from vinemap.graph.model import CodeGraph
from vinemap.rank.bm25 import _doc_text

_MODEL_NAME = "all-MiniLM-L6-v2"
_CACHE_FILE = "emb_cache.json"


def embeddings_available() -> bool:
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        return True
    except ImportError:
        return False


def _cache_path(root: str) -> str:
    return os.path.join(root, GRAPH_DIR, _CACHE_FILE)


def _load_cache(root: str) -> dict:
    path = _cache_path(root)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(root: str, cache: dict) -> None:
    from vinemap.graph.store import atomic_write_json

    atomic_write_json(_cache_path(root), cache)


def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def _embed_texts(model, texts: List[str]) -> List[List[float]]:
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def _cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _vector_for_file(
    graph: CodeGraph,
    path: str,
    cache: dict,
    model,
) -> Optional[List[float]]:
    pf = graph.files[path]
    key = pf.content_hash or hashlib.sha256(_doc_text(graph, path).encode()).hexdigest()[:16]
    if key in cache:
        return cache[key]
    vec = _embed_texts(model, [_doc_text(graph, path)])[0]
    cache[key] = vec
    return vec


def embedding_scores(
    graph: CodeGraph,
    query: str,
    project_root: Optional[str] = None,
) -> Dict[str, float]:
    """Cosine similarity scores per file. Returns {} when extra not installed."""
    if not embeddings_available() or not graph.files:
        return {}

    root = project_root or "."
    cache = _load_cache(root)
    model = _model()
    query_vec = _embed_texts(model, [query])[0]

    scores: Dict[str, float] = {}
    dirty = False
    for path in graph.files:
        vec = _vector_for_file(graph, path, cache, model)
        if vec is None:
            continue
        if graph.files[path].content_hash and graph.files[path].content_hash not in cache:
            dirty = True
        sim = _cosine(query_vec, vec)
        if sim > 0.05:
            scores[path] = sim * 10.0

    if dirty and project_root:
        _save_cache(root, cache)
    elif project_root and any(
        graph.files[p].content_hash not in cache for p in graph.files if graph.files[p].content_hash
    ):
        _save_cache(root, cache)

    return scores


def using_embeddings() -> bool:
    return embeddings_available()
