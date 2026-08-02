"""Tests for optional embedding ranking (skipped without vinemap[embeddings])."""

import pytest

from vinemap.graph.model import CodeGraph
from vinemap.rank.embeddings import embeddings_available, embedding_scores
from vinemap.rank.ranker import rank_files
from vinemap.scanner.walker import scan_project

pytestmark = pytest.mark.skipif(
    not embeddings_available(),
    reason="embeddings extra not installed (pip install vinemap[embeddings])",
)


def test_embedding_scores_returns_similar_files(project):
    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    scores = embedding_scores(graph, "password hashing login", project_root=project)
    assert scores
    assert max(scores, key=scores.get) == "app/auth.py"


def test_ranker_includes_embedding_signal(project):
    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    ranked = rank_files(graph, "password hashing", k=3, project_root=project)
    assert ranked[0][0] == "app/auth.py"
