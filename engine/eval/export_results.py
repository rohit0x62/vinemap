#!/usr/bin/env python3
"""Export golden eval results to JSON for the marketing site benchmarks page."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.harness import GOLDEN_DIR, run_eval

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "website" / "app" / "benchmarks" / "eval-data.json"


def export_results(*, reindex: bool = True) -> dict:
    suites = []
    total_cases = 0
    total_hits = 0
    precision_sum = 0.0

    for path in sorted(GOLDEN_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            meta = json.load(f)
        report = run_eval(path, reindex=reindex)
        n = len(report.cases)
        hits = sum(1 for c in report.cases if c.hit)
        total_cases += n
        total_hits += hits
        precision_sum += report.mean_precision * n
        suites.append(
            {
                "name": report.name,
                "k": report.k,
                "mean_precision": round(report.mean_precision, 4),
                "hit_rate": round(report.hit_rate, 4),
                "cases": [
                    {
                        "query": c.query,
                        "expected": c.expected,
                        "retrieved": c.retrieved[: report.k],
                        "precision_at_k": round(c.precision_at_k, 4),
                        "hit": c.hit,
                    }
                    for c in report.cases
                ],
            }
        )

    overall = precision_sum / max(total_cases, 1)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "k": suites[0]["k"] if suites else 5,
        "suites": len(suites),
        "total_cases": total_cases,
        "total_hits": total_hits,
        "mean_precision": round(overall, 4),
        "hit_rate": round(total_hits / max(total_cases, 1), 4),
        "eval_suites": suites,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export eval results for website")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT})",
    )
    parser.add_argument("--no-reindex", action="store_true")
    args = parser.parse_args()

    data = export_results(reindex=not args.no_reindex)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"wrote {args.out} ({data['total_cases']} cases, mean P@{data['k']}={data['mean_precision']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
