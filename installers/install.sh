#!/usr/bin/env bash
# Vinemap one-line installer for macOS & Linux.
#   curl -sSL https://<your-domain>/install.sh | bash
set -euo pipefail

BOLD=$(tput bold 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

say() { echo "${BOLD}[vinemap]${RESET} $*"; }
die() { echo "${BOLD}[vinemap] error:${RESET} $*" >&2; exit 1; }

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PY=$(find_python) || die "Python 3.9+ not found. Install it via your package manager (brew install python / apt install python3) and re-run."
say "using $($PY --version 2>&1)"

VINEMAP_HOME="${VINEMAP_HOME:-$HOME/.vinemap-cli}"
say "installing into $VINEMAP_HOME"

"$PY" -m venv "$VINEMAP_HOME/venv" 2>/dev/null || {
  # Debian/Ubuntu often ships python without venv
  if command -v apt-get >/dev/null 2>&1; then
    say "python3-venv missing — trying: sudo apt-get install -y python3-venv"
    sudo apt-get install -y python3-venv
    "$PY" -m venv "$VINEMAP_HOME/venv"
  else
    die "could not create a virtualenv with $PY"
  fi
}

"$VINEMAP_HOME/venv/bin/pip" install --quiet --upgrade pip
"$VINEMAP_HOME/venv/bin/pip" install --quiet vinemap

mkdir -p "$HOME/.local/bin"
ln -sf "$VINEMAP_HOME/venv/bin/vinemap" "$HOME/.local/bin/vinemap"

shell_rc() {
  case "${SHELL:-}" in
    */zsh) echo "$HOME/.zshrc" ;;
    */bash) echo "$HOME/.bashrc" ;;
    *) echo "$HOME/.profile" ;;
  esac
}

ensure_local_bin_path() {
  local bin="$HOME/.local/bin"
  case ":$PATH:" in
    *":$bin:"*) return 0 ;;
  esac
  local rc
  rc=$(shell_rc)
  touch "$rc"
  if grep -qF '.local/bin' "$rc" 2>/dev/null; then
    say "~/.local/bin already listed in $rc — run: source $rc"
    return 0
  fi
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
  say "added ~/.local/bin to PATH in $rc — run: source $rc"
}

ensure_local_bin_path

say "installed. Get started:"
echo "    cd your-project"
echo "    vinemap quickstart     # index, connect agent, try a query"
echo "    vinemap index .        # or build the code graph manually"
echo "    vinemap mcp .          # start the MCP server for your agent"
