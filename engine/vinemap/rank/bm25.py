"""BM25-style lexical scoring over graph text fields (dependency-free)."""

import math
import re
from collections import Counter
from typing import Dict, List, Set

from vinemap.graph.model import CodeGraph

_WORD = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
_K1 = 1.2
_B = 0.75


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD.findall(text) if len(w) > 2]


def _doc_text(graph: CodeGraph, path: str) -> str:
    pf = graph.files[path]
    parts = [path.replace("/", " "), pf.module_docstring]
    for sym in pf.symbols:
        parts.append(sym.name)
        parts.append(sym.signature)
        parts.append(sym.docstring)
    return " ".join(parts)


def build_corpus(graph: CodeGraph) -> Dict[str, List[str]]:
    return {path: _tokenize(_doc_text(graph, path)) for path in graph.files}


def bm25_scores(graph: CodeGraph, query: str) -> Dict[str, float]:
    """Return BM25 scores per file path for a query."""
    terms = _tokenize(query)
    if not terms:
        return {}

    corpus = build_corpus(graph)
    if not corpus:
        return {}

    doc_lens = {p: len(toks) for p, toks in corpus.items()}
    avgdl = sum(doc_lens.values()) / max(len(doc_lens), 1)
    N = len(corpus)

    # document frequency
    df: Counter = Counter()
    for toks in corpus.values():
        for t in set(toks):
            df[t] += 1

    scores: Dict[str, float] = {}
    for path, toks in corpus.items():
        tf = Counter(toks)
        dl = doc_lens[path]
        s = 0.0
        for term in terms:
            if term not in df:
                continue
            idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf.get(term, 0)
            denom = freq + _K1 * (1 - _B + _B * dl / avgdl)
            s += idf * (freq * (_K1 + 1)) / max(denom, 1e-9)
        if s > 0:
            scores[path] = s
    return scores
