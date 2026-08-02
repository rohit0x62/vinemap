#!/usr/bin/env bash
# Secure PyPI publish wrapper — token via env or ~/.config/vinemap/pypi-token only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 tools/pypi_publish.py "$@"
