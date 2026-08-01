"""Parser registry: maps file extensions to the best available parser."""

from typing import Dict, Optional

from vinemap.scanner.parsers.base import ParsedFile, Parser, Symbol
from vinemap.scanner.parsers.python_parser import PythonParser
from vinemap.scanner.parsers.regex_parser import RegexParser

__all__ = ["ParsedFile", "Parser", "Symbol", "get_parser", "supported_extensions"]

_python = PythonParser()
_regex = RegexParser()

_REGISTRY: Dict[str, Parser] = {".py": _python}
for _ext in _regex.extensions:
    _REGISTRY.setdefault(_ext, _regex)


def get_parser(path: str) -> Optional[Parser]:
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _REGISTRY.get(ext)


def supported_extensions() -> list:
    return sorted(_REGISTRY.keys())
