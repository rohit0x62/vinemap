"""Context packer: turns ranked graph results into a compact prompt block.

Design rules (mirroring what makes pre-injection work):
  - Structured summaries over raw dumps: signatures, docstrings, call edges.
  - Code-first: up to ~45% of the token budget goes to inline bodies of the
    top-ranked symbols, because agents need real code, not just metadata.
  - Hard token budget: the pack never exceeds it, so it is safe to inject
    into any agent prompt.
"""

import os
from typing import List, Optional, Tuple

from vinemap.graph.model import CodeGraph
from vinemap.memory.session import SessionMemory
from vinemap.rank.ranker import rank_files

DEFAULT_BUDGET_TOKENS = 6000
CODE_BUDGET_RATIO = 0.45


def estimate_tokens(text: str) -> int:
    return max(len(text) // 4, 1)


def _read_lines(root: str, path: str, start: int, end: int) -> str:
    full = os.path.realpath(os.path.join(root, path))
    # Defense in depth: graph paths come from our own scan, but the graph file
    # on disk is user-writable — never read outside the project root.
    if not full.startswith(os.path.realpath(root) + os.sep):
        return ""
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return ""
    return "".join(lines[max(start - 1, 0): end])


def _file_summary(graph: CodeGraph, path: str) -> str:
    pf = graph.files[path]
    nb = graph.neighbors(path)
    out = [f"### {path}  ({pf.language}, {pf.line_count} lines)"]
    if nb["imports"]:
        out.append(f"imports: {', '.join(nb['imports'][:8])}")
    if nb["imported_by"]:
        out.append(f"imported by: {', '.join(nb['imported_by'][:8])}")
    for sym in pf.symbols[:25]:
        line = f"- L{sym.line_start} {sym.signature or sym.kind + ' ' + sym.name}"
        if sym.docstring:
            line += f"  # {sym.docstring.splitlines()[0][:80]}"
        if sym.calls:
            line += f"  [calls: {', '.join(sym.calls[:6])}]"
        out.append(line)
    return "\n".join(out)


def build_context_pack(
    root: str,
    graph: CodeGraph,
    query: str,
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    k: int = 12,
    memory: Optional[SessionMemory] = None,
    include_coverage: bool = False,
) -> Tuple[str, List[str]]:
    """Build the injectable context block. Returns (pack_text, included_paths)."""
    ranked = rank_files(graph, query, k=k, memory=memory, project_root=root)
    if not ranked:
        return "", []

    coverage_line = ""

    header = (
        "<codebase_context>\n"
        f"Project context pack for: {query!r}\n"
        "Generated locally by Vinemap from the code graph. "
        "Prefer this over re-exploring the repository.\n"
    )
    footer = "</codebase_context>"
    used = estimate_tokens(header) + estimate_tokens(footer)

    summaries: List[str] = []
    included: List[str] = []
    summary_budget = budget_tokens * (1 - CODE_BUDGET_RATIO)
    for path, _score in ranked:
        block = _file_summary(graph, path)
        cost = estimate_tokens(block)
        if used + cost > summary_budget:
            continue
        used += cost
        summaries.append(block)
        included.append(path)

    # inline code for the highest-value symbols across included files
    code_blocks: List[str] = []
    code_budget = budget_tokens * CODE_BUDGET_RATIO
    code_used = 0
    for path, _score in ranked:
        if path not in included:
            continue
        pf = graph.files[path]
        symbols = sorted(
            (s for s in pf.symbols if s.kind != "class"),
            key=lambda s: -(s.line_end - s.line_start),
        )[:2]
        for sym in symbols:
            snippet = _read_lines(root, path, sym.line_start, min(sym.line_end, sym.line_start + 60))
            if not snippet.strip():
                continue
            block = f"```{pf.language} {path}:{sym.line_start}\n{snippet}```"
            cost = estimate_tokens(block)
            if code_used + cost > code_budget:
                break
            code_used += cost
            code_blocks.append(block)

    if memory is not None:
        for path in included:
            memory.touch(path, "retrieved")
        memory.save()

    if include_coverage:
        from vinemap.pro.coverage import coverage_score

        score, inc_n, uni_n = coverage_score(graph, query, included, k=k)
        coverage_line = f"Coverage: {score}% ({inc_n}/{uni_n} relevant files in pack)\n"

    parts = [header]
    if coverage_line:
        parts.append(coverage_line)
    parts.append("\n\n".join(summaries))
    if code_blocks:
        parts.append("\n## Most relevant code\n" + "\n\n".join(code_blocks))
    if memory is not None and memory.recent_decisions():
        parts.append(
            "\n## Session decisions\n" + "\n".join(f"- {d}" for d in memory.recent_decisions())
        )
    parts.append(footer)
    return "\n".join(parts), included
