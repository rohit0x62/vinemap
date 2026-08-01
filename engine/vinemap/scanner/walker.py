"""Project walker: finds source files, respecting ignore rules and caching."""

import hashlib
import os
from typing import Iterator, List, Optional, Set, Tuple

from vinemap.scanner.parsers import ParsedFile, get_parser

DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".vinemap", ".dual-graph", "dist", "build", ".next", "target", "vendor",
    ".idea", ".vscode", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "site-packages", ".tox", ".cache",
}

MAX_FILE_BYTES = 1_500_000  # skip generated/minified monsters


def _load_vinemapignore(root: str) -> Set[str]:
    path = os.path.join(root, ".vinemapignore")
    extra: Set[str] = set()
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    extra.add(line.rstrip("/"))
    return extra


def iter_source_files(root: str) -> Iterator[str]:
    """Yield project-relative posix paths of parseable source files.

    Symlinks (directory and file) are never followed: a link pointing outside
    the project must not pull external files into the graph.
    """
    ignore = DEFAULT_IGNORE_DIRS | _load_vinemapignore(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith(".")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            if get_parser(name) is None:
                continue
            if os.path.islink(full):
                continue
            try:
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield os.path.relpath(full, root).replace(os.sep, "/")


def content_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()[:16]


def scan_project(
    root: str,
    previous: Optional[dict] = None,
    max_files: Optional[int] = None,
) -> Tuple[List[ParsedFile], int, int]:
    """Parse all source files under root.

    `previous` maps path -> ParsedFile dict from a prior scan; unchanged files
    (same content hash) are reused so incremental re-index is sub-second.

    Returns (parsed_files, parsed_count, cached_count).
    """
    previous = previous or {}
    parsed: List[ParsedFile] = []
    n_parsed = n_cached = 0

    for rel in iter_source_files(root):
        if max_files is not None and len(parsed) >= max_files:
            break
        full = os.path.join(root, rel)
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                source = f.read()
        except OSError:
            continue
        digest = content_hash(source)
        prev = previous.get(rel)
        if prev is not None and prev.get("content_hash") == digest:
            parsed.append(ParsedFile.from_dict(prev))
            n_cached += 1
            continue
        parser = get_parser(rel)
        if parser is None:
            continue
        pf = parser.parse(rel, source)
        pf.content_hash = digest
        parsed.append(pf)
        n_parsed += 1

    return parsed, n_parsed, n_cached
