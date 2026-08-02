#!/usr/bin/env bash
# Vinemap guided setup — run inside your project after install.
#   curl -sSL https://raw.githubusercontent.com/rohit0x62/vinemap/main/installers/quickstart.sh | bash
# Or locally: vinemap quickstart
set -euo pipefail

BOLD=$(tput bold 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)
die() { echo "${BOLD}[vinemap] error:${RESET} $*" >&2; exit 1; }

if ! command -v vinemap >/dev/null 2>&1; then
  die "vinemap not found. Install first:
    curl -fsSL https://raw.githubusercontent.com/rohit0x62/vinemap/main/installers/install.sh | bash
  or: pip install vinemap"
fi

exec vinemap quickstart "$@"
