"""Parser registry: maps file extensions to the best available parser."""

from typing import Dict, Optional

from vinemap.scanner.parsers.base import ParsedFile, Parser, Symbol
from vinemap.scanner.parsers.python_parser import PythonParser
from vinemap.scanner.parsers.regex_parser import RegexParser

__all__ = [
    "ParsedFile",
    "Parser",
    "Symbol",
    "get_parser",
    "supported_extensions",
    "using_treesitter",
]

_python = PythonParser()
_regex = RegexParser()
_treesitter: Optional[Parser] = None
_using_treesitter = False


def _init_treesitter() -> Optional[Parser]:
    global _treesitter, _using_treesitter
    if _treesitter is not None:
        return _treesitter
    try:
        from vinemap.scanner.parsers.treesitter_parser import TreeSitterParser

        _treesitter = TreeSitterParser()
        _using_treesitter = True
        return _treesitter
    except ImportError:
        return None


def _build_registry() -> Dict[str, Parser]:
    reg: Dict[str, Parser] = {".py": _python}
    ts = _init_treesitter()
    fallback = ts if ts is not None else _regex
    for ext in fallback.extensions:
        reg.setdefault(ext, fallback)
    return reg


_REGISTRY = _build_registry()


def get_parser(path: str) -> Optional[Parser]:
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _REGISTRY.get(ext)


def supported_extensions() -> list:
    return sorted(_REGISTRY.keys())


def using_treesitter() -> bool:
    _init_treesitter()
    return _using_treesitter
