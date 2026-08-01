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

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *)
    SHELL_RC="$HOME/.zshrc"
    [ -n "${BASH_VERSION:-}" ] && SHELL_RC="$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    say "added ~/.local/bin to PATH in $SHELL_RC — run: source $SHELL_RC"
    ;;
esac

say "installed. Get started:"
echo "    cd your-project"
echo "    vinemap index .      # build the code graph"
echo "    vinemap mcp .        # start the MCP server for your agent"
