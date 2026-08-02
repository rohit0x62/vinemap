"""Precision@k evaluation harness for Vinemap file ranking.

Loads golden query sets (JSON) and scores retrieval against expected top files.
Supports the engine repo itself and bundled local fixtures under ``eval/fixtures/``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, save_graph
from vinemap.rank.ranker import rank_files
from vinemap.scanner.walker import scan_project

EVAL_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVAL_DIR / "fixtures"
GOLDEN_DIR = EVAL_DIR / "golden"
ENGINE_ROOT = EVAL_DIR.parent


@dataclass(frozen=True)
class CaseResult:
    query: str
    expected: List[str]
    retrieved: List[str]
    project: str
    precision_at_k: float
    hit: bool


@dataclass
class EvalReport:
    name: str
    k: int
    cases: List[CaseResult] = field(default_factory=list)

    @property
    def mean_precision(self) -> float:
        if not self.cases:
            return 0.0
        return sum(c.precision_at_k for c in self.cases) / len(self.cases)

    @property
    def hit_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.hit) / len(self.cases)


def precision_at_k(expected: Sequence[str], retrieved: Sequence[str], k: int) -> float:
    """Fraction of expected files that appear in the top-k retrieved paths."""
    top_k = list(retrieved[:k])
    if not expected:
        return 0.0
    hits = sum(1 for path in expected if path in top_k)
    return hits / len(expected)


def _resolve_project(case: Dict[str, Any], default_root: str) -> str:
    fixture = case.get("fixture")
    if fixture:
        return str((FIXTURES_DIR / fixture).resolve())
    project = case.get("project", default_root)
    if project == ".":
        project = str(ENGINE_ROOT)
    return os.path.abspath(project)


def _index(root: str) -> CodeGraph:
    files, _, _ = scan_project(root)
    graph = CodeGraph.build(files)
    save_graph(root, graph)
    return graph


def _load_or_index(root: str, reindex: bool) -> CodeGraph:
    if reindex:
        return _index(root)
    graph = load_graph(root)
    if graph is None:
        return _index(root)
    return graph


def load_golden(path: Path | str) -> Dict[str, Any]:
    golden_path = Path(path)
    with golden_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_eval(
    golden_path: Path | str,
    *,
    default_project: Optional[str] = None,
    k: Optional[int] = None,
    reindex: bool = True,
) -> EvalReport:
    """Run precision@k for every case in a golden JSON file."""
    data = load_golden(golden_path)
    name = data.get("name", Path(golden_path).stem)
    eval_k = k if k is not None else int(data.get("k", 5))
    default_root = default_project or data.get("project", str(ENGINE_ROOT))
    if default_root == ".":
        default_root = str(ENGINE_ROOT)
    default_root = os.path.abspath(default_root)

    graphs: Dict[str, CodeGraph] = {}
    results: List[CaseResult] = []

    for case in data["cases"]:
        query = case["query"]
        expected = list(case["expected"])
        root = _resolve_project(case, default_root)

        if root not in graphs:
            graphs[root] = _load_or_index(root, reindex=reindex)

        ranked = rank_files(graphs[root], query, k=eval_k, project_root=root)
        retrieved = [path for path, _ in ranked]
        p_at_k = precision_at_k(expected, retrieved, eval_k)
        results.append(
            CaseResult(
                query=query,
                expected=expected,
                retrieved=retrieved,
                project=root,
                precision_at_k=p_at_k,
                hit=any(path in retrieved[:eval_k] for path in expected),
            )
        )

    return EvalReport(name=name, k=eval_k, cases=results)


def format_report(report: EvalReport) -> str:
    lines = [
        f"Eval: {report.name}  (precision@{report.k})",
        f"Mean precision@{report.k}: {report.mean_precision:.3f}",
        f"Hit rate: {report.hit_rate:.0%} ({sum(c.hit for c in report.cases)}/{len(report.cases)})",
        "",
    ]
    for case in report.cases:
        status = "PASS" if case.hit else "FAIL"
        lines.append(f"[{status}] {case.query!r}")
        lines.append(f"  expected: {', '.join(case.expected) or '(none)'}")
        if case.retrieved:
            preview = ", ".join(case.retrieved[: report.k])
            lines.append(f"  top-{report.k}: {preview}")
        else:
            lines.append("  top-k: (no matches)")
        lines.append(f"  precision@{report.k}: {case.precision_at_k:.3f}")
        lines.append("")
    return "\n".join(lines).rstrip()


def run_all_evals(
    *,
    reindex: bool = True,
    golden_dir: Optional[Path] = None,
) -> List[EvalReport]:
    """Run every golden JSON file in eval/golden/."""
    directory = golden_dir or GOLDEN_DIR
    reports: List[EvalReport] = []
    for path in sorted(directory.glob("*.json")):
        reports.append(run_eval(path, reindex=reindex))
    return reports


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run Vinemap precision@k golden evals")
    parser.add_argument(
        "golden",
        nargs="?",
        default=str(GOLDEN_DIR / "vinemap_self.json"),
        help="Path to golden JSON (default: eval/golden/vinemap_self.json)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all golden sets under eval/golden/",
    )
    parser.add_argument("--k", type=int, help="Override top-k from golden file")
    parser.add_argument(
        "--project",
        help="Override default project root (golden file project field otherwise)",
    )
    parser.add_argument(
        "--min-precision",
        type=float,
        default=None,
        help="Exit 1 if mean precision@k is below this threshold",
    )
    parser.add_argument(
        "--no-reindex",
        action="store_true",
        help="Reuse existing .vinemap/graph.json when present",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.all:
        exit_code = 0
        for path in sorted(GOLDEN_DIR.glob("*.json")):
            data = load_golden(path)
            report = run_eval(path, reindex=not args.no_reindex)
            print(format_report(report))
            print("")
            min_p = data.get("min_mean_precision")
            if min_p is not None and report.mean_precision < float(min_p):
                print(
                    f"FAIL: {report.name} mean precision@{report.k} "
                    f"{report.mean_precision:.3f} < {float(min_p):.3f}",
                    flush=True,
                )
                exit_code = 1
        return exit_code

    golden_data = load_golden(args.golden)
    min_precision = args.min_precision
    if min_precision is None:
        min_precision = golden_data.get("min_mean_precision")

    report = run_eval(
        args.golden,
        default_project=args.project,
        k=args.k,
        reindex=not args.no_reindex,
    )
    print(format_report(report))

    if min_precision is not None and report.mean_precision < float(min_precision):
        print(
            f"\nFAIL: mean precision@{report.k} "
            f"{report.mean_precision:.3f} < {float(min_precision):.3f}",
            flush=True,
        )
        return 1
    return 0
