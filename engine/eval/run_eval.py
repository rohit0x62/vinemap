#!/usr/bin/env python3
"""CLI entry point for Vinemap precision@k golden evals."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.harness import main

if __name__ == "__main__":
    raise SystemExit(main())
