"""Pre-injection: build context packs for agent hooks before the first tool call."""

import os
import sys
from typing import Optional, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph
from vinemap.license import effective_max_files
from vinemap.memory.session import SessionMemory
from vinemap.pack.packer import DEFAULT_BUDGET_TOKENS, build_context_pack, estimate_tokens
from vinemap.scanner.walker import scan_project


def ensure_graph(root: str) -> CodeGraph:
    graph = load_graph(root)
    if graph is not None:
        return graph
    files, _, _ = scan_project(root, max_files=effective_max_files(None))
    graph = CodeGraph.build(files)
    from vinemap.graph.store import save_graph

    save_graph(root, graph)
    return graph


def build_injection_pack(
    root: str,
    query: str,
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    include_coverage: bool = False,
) -> Tuple[str, int]:
    """Build a pack suitable for prompt injection. Returns (pack, token_estimate)."""
    root = os.path.abspath(root)
    graph = ensure_graph(root)
    memory = SessionMemory(root)
    use_coverage = include_coverage
    pack, _included = build_context_pack(
        root,
        graph,
        query,
        budget_tokens=budget_tokens,
        memory=memory,
        include_coverage=use_coverage,
    )
    if not pack:
        return "", 0
    return pack, estimate_tokens(pack)


def extract_query_from_prompt(prompt: str) -> str:
    """Heuristic: use the user's prompt as the retrieval query."""
    lines = [ln.strip() for ln in prompt.strip().splitlines() if ln.strip()]
    if not lines:
        return "main entry points and core modules"
    # Prefer last non-empty line (often the actual ask)
    query = lines[-1][:500]
    return query or "main entry points and core modules"


def emit_injection(pack: str, stream=None) -> None:
    """Write pack to stdout (for hook scripts)."""
    out = stream or sys.stdout
    out.write(pack)
    if not pack.endswith("\n"):
        out.write("\n")
    out.flush()
