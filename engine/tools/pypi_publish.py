#!/usr/bin/env python3
"""Secure local PyPI publish helper for Vinemap maintainers.

The API token is NEVER read from argv, git, or MCP tool arguments — only from:
  1. PYPI_API_TOKEN or TWINE_PASSWORD environment variables
  2. An optional local file (default ~/.config/vinemap/pypi-token, mode 0600)

Usage:
  python tools/pypi_publish.py status
  python tools/pypi_publish.py build
  python tools/pypi_publish.py publish --confirm v0.1.2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

ENGINE_DIR = Path(__file__).resolve().parents[1]
PYPROJECT = ENGINE_DIR / "pyproject.toml"
DIST_DIR = ENGINE_DIR / "dist"
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "vinemap" / "pypi-token"
PYPI_PROJECT_URL = "https://pypi.org/pypi/vinemap/json"


class PublishError(RuntimeError):
    pass


def read_local_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise PublishError(f"Could not find version in {PYPROJECT}")
    return match.group(1)


def pypi_released_version() -> Optional[str]:
    try:
        with urllib.request.urlopen(PYPI_PROJECT_URL, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise PublishError(f"PyPI lookup failed: HTTP {exc.code}") from exc
    except OSError as exc:
        raise PublishError(f"PyPI lookup failed: {exc}") from exc
    info = data.get("info") or {}
    version = info.get("version")
    return str(version) if version else None


def _load_token_file(path: Path) -> str:
    if not path.is_file():
        raise PublishError(
            f"Token file not found: {path}\n"
            "Set PYPI_API_TOKEN or create the file (see engine/PUBLISH.md)."
        )
    mode = path.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
        raise PublishError(
            f"Refusing to read token file with loose permissions: {path}\n"
            f"Run: chmod 600 {path}"
        )
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise PublishError(f"Token file is empty: {path}")
    if "pypi-" not in token:
        raise PublishError("Token file does not look like a PyPI API token (expected pypi-… prefix)")
    return token


def load_token(token_file: Optional[Path] = None) -> str:
    for env_name in ("PYPI_API_TOKEN", "TWINE_PASSWORD"):
        token = os.environ.get(env_name, "").strip()
        if token:
            return token
    path = token_file or DEFAULT_TOKEN_FILE
    return _load_token_file(path)


def token_source() -> str:
    if os.environ.get("PYPI_API_TOKEN", "").strip():
        return "PYPI_API_TOKEN env"
    if os.environ.get("TWINE_PASSWORD", "").strip():
        return "TWINE_PASSWORD env"
    if DEFAULT_TOKEN_FILE.is_file():
        return f"file:{DEFAULT_TOKEN_FILE}"
    return "not configured"


def _run(cmd: list[str], *, env: Optional[dict] = None, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(
        cmd,
        cwd=str(cwd or ENGINE_DIR),
        env=merged,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise PublishError(f"Command failed ({' '.join(cmd)}): {detail}")
    return result


def ensure_build_tools() -> None:
    for module in ("build", "twine"):
        try:
            __import__(module)
        except ImportError as exc:
            raise PublishError(
                f"Missing {module}. Install with: pip install build twine"
            ) from exc


def build_package(*, clean: bool = True) -> list[Path]:
    ensure_build_tools()
    if clean and DIST_DIR.exists():
        for artifact in DIST_DIR.glob("vinemap-*"):
            artifact.unlink()
    _run([sys.executable, "-m", "build"], cwd=ENGINE_DIR)
    artifacts = sorted(DIST_DIR.glob("vinemap-*"))
    if not artifacts:
        raise PublishError("Build produced no artifacts in dist/")
    _run([sys.executable, "-m", "twine", "check", *[str(a) for a in artifacts]], cwd=ENGINE_DIR)
    return artifacts


def upload_package(token: str, *, artifacts: Optional[list[Path]] = None) -> str:
    ensure_build_tools()
    files = artifacts or sorted(DIST_DIR.glob("vinemap-*"))
    if not files:
        raise PublishError("No dist/ artifacts — run build first")
    env = {
        "TWINE_USERNAME": "__token__",
        "TWINE_PASSWORD": token,
        "TWINE_NON_INTERACTIVE": "1",
    }
    _run(
        [sys.executable, "-m", "twine", "upload", "--non-interactive", *[str(f) for f in files]],
        env=env,
        cwd=ENGINE_DIR,
    )
    return f"Uploaded {len(files)} artifact(s) to PyPI"


def status_report() -> dict:
    local = read_local_version()
    remote = pypi_released_version()
    return {
        "local_version": local,
        "pypi_version": remote,
        "ahead_of_pypi": remote is None or local != remote,
        "token_configured": token_source() != "not configured",
        "token_source": token_source(),
        "engine_dir": str(ENGINE_DIR),
    }


def publish(*, confirm: str, token_file: Optional[Path] = None, skip_build: bool = False) -> dict:
    local = read_local_version()
    if confirm != local:
        raise PublishError(
            f"Confirmation mismatch: expected --confirm {local!r}, got {confirm!r}"
        )
    remote = pypi_released_version()
    if remote == local:
        raise PublishError(
            f"Version {local} is already on PyPI. Bump version in pyproject.toml first."
        )
    token = load_token(token_file)
    artifacts = None if skip_build else build_package()
    message = upload_package(token, artifacts=artifacts)
    return {
        **status_report(),
        "uploaded": True,
        "message": message,
        "artifacts": [a.name for a in (artifacts or sorted(DIST_DIR.glob("vinemap-*")))],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Secure Vinemap PyPI publish helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show local vs PyPI version and token source")

    p_build = sub.add_parser("build", help="build wheel/sdist and run twine check")
    p_build.add_argument("--keep-dist", action="store_true", help="do not clean dist/ first")

    p_pub = sub.add_parser("publish", help="build (unless --skip-build) and upload to PyPI")
    p_pub.add_argument(
        "--confirm",
        required=True,
        help="Must exactly match version in pyproject.toml (safety gate)",
    )
    p_pub.add_argument("--skip-build", action="store_true", help="upload existing dist/ artifacts")
    p_pub.add_argument(
        "--token-file",
        type=Path,
        default=None,
        help=f"Token file path (default {DEFAULT_TOKEN_FILE})",
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            report = status_report()
            print(json.dumps(report, indent=2))
            return 0
        if args.command == "build":
            artifacts = build_package(clean=not args.keep_dist)
            print(json.dumps({"built": [a.name for a in artifacts]}, indent=2))
            return 0
        if args.command == "publish":
            report = publish(
                confirm=args.confirm,
                token_file=args.token_file,
                skip_build=args.skip_build,
            )
            print(json.dumps(report, indent=2))
            return 0
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
