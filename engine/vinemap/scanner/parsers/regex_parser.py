"""Heuristic regex parser for languages without a precise parser yet.

Covers the top languages well enough to build a useful graph. The roadmap
replaces this with tree-sitter grammars per language (see optional extra
`vinemap[treesitter]`), keeping this as the zero-dependency fallback.
"""

import re
from typing import Dict, List, Pattern

from vinemap.scanner.parsers.base import ParsedFile, Symbol

# language -> (extensions, function patterns, class patterns, import patterns)
_FN: Dict[str, List[Pattern]] = {
    "javascript": [
        re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(", re.M),
        re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?[\w\s,{}:$\[\]]*\)?\s*=>", re.M),
    ],
    "go": [re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)\s*\(", re.M)],
    "java": [
        re.compile(
            r"^\s*(?:public|private|protected|static|final|abstract|synchronized|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^;]*\)\s*(?:throws [\w,\s]+)?\{",
            re.M,
        )
    ],
    "rust": [re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)", re.M)],
    "c": [re.compile(r"^[\w\*\s]+\s+\*?(\w+)\s*\([^;{]*\)\s*\{", re.M)],
    "cpp": [re.compile(r"^[\w\*&:<>,\s]+\s+\*?([\w:]+)\s*\([^;{]*\)\s*(?:const\s*)?\{", re.M)],
    "csharp": [
        re.compile(
            r"^\s*(?:public|private|protected|internal|static|virtual|override|async|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^;]*\)\s*\{",
            re.M,
        )
    ],
    "ruby": [re.compile(r"^\s*def\s+(?:self\.)?([\w?!]+)", re.M)],
    "php": [re.compile(r"^\s*(?:public|private|protected|static|\s)*function\s+(\w+)\s*\(", re.M)],
    "kotlin": [re.compile(r"^\s*(?:override\s+|suspend\s+|private\s+|public\s+|internal\s+)*fun\s+(?:<[^>]+>\s+)?([A-Za-z_]\w*)", re.M)],
    "swift": [re.compile(r"^\s*(?:public|private|internal|open|static|\s)*func\s+([A-Za-z_]\w*)", re.M)],
}

_CLS: Dict[str, List[Pattern]] = {
    "javascript": [re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)],
    "go": [re.compile(r"^type\s+([A-Za-z_]\w*)\s+(?:struct|interface)\b", re.M)],
    "java": [re.compile(r"^\s*(?:public\s+|abstract\s+|final\s+)*(?:class|interface|enum|record)\s+(\w+)", re.M)],
    "rust": [re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)", re.M)],
    "cpp": [re.compile(r"^\s*(?:class|struct)\s+(\w+)", re.M)],
    "csharp": [re.compile(r"^\s*(?:public\s+|internal\s+|abstract\s+|sealed\s+|partial\s+)*(?:class|interface|struct|record|enum)\s+(\w+)", re.M)],
    "ruby": [re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)", re.M)],
    "php": [re.compile(r"^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait)\s+(\w+)", re.M)],
    "kotlin": [re.compile(r"^\s*(?:data\s+|sealed\s+|abstract\s+|open\s+)*(?:class|interface|object)\s+([A-Za-z_]\w*)", re.M)],
    "swift": [re.compile(r"^\s*(?:public\s+|open\s+|final\s+)*(?:class|struct|enum|protocol)\s+([A-Za-z_]\w*)", re.M)],
}

_IMP: Dict[str, List[Pattern]] = {
    "javascript": [
        re.compile(r"""(?:import\s[\w\s{},*$]*?from\s*|import\s*\(\s*|require\s*\(\s*)['"]([^'"]+)['"]""", re.M),
        re.compile(r"""^import\s+['"]([^'"]+)['"]""", re.M),
    ],
    "go": [re.compile(r'^\s*(?:\w+\s+)?"([\w./\-]+)"', re.M)],
    "java": [re.compile(r"^import\s+(?:static\s+)?([\w.]+)", re.M)],
    "rust": [re.compile(r"^\s*use\s+([\w:]+)", re.M)],
    "c": [re.compile(r'^#include\s*[<"]([^>"]+)[>"]', re.M)],
    "cpp": [re.compile(r'^#include\s*[<"]([^>"]+)[>"]', re.M)],
    "csharp": [re.compile(r"^using\s+([\w.]+)\s*;", re.M)],
    "ruby": [re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""", re.M)],
    "php": [re.compile(r"^use\s+([\w\\]+)", re.M)],
    "kotlin": [re.compile(r"^import\s+([\w.]+)", re.M)],
    "swift": [re.compile(r"^import\s+(\w+)", re.M)],
}

_EXT_TO_LANG = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "javascript", ".tsx": "javascript", ".mts": "javascript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c", ".h": "c",
    ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin", ".kts": "kotlin",
    ".swift": "swift",
}


class RegexParser:
    """Best-effort symbol and import extraction across ~12 languages."""

    languages = sorted(set(_EXT_TO_LANG.values()))
    extensions = list(_EXT_TO_LANG.keys())

    def parse(self, path: str, source: str) -> ParsedFile:
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        lang = _EXT_TO_LANG.get(ext, "unknown")
        result = ParsedFile(path=path, language=lang, line_count=source.count("\n") + 1)
        if lang == "unknown":
            return result

        line_of = _LineIndex(source)
        seen = set()
        for kind, table in (("function", _FN), ("class", _CLS)):
            for pattern in table.get(lang, []):
                for m in pattern.finditer(source):
                    name = m.group(1)
                    key = (name, kind)
                    if key in seen:
                        continue
                    seen.add(key)
                    line = line_of.at(m.start())
                    sig = source[m.start(): source.find("\n", m.start())].strip()[:160]
                    result.symbols.append(
                        Symbol(name=name, kind=kind, line_start=line, line_end=line, signature=sig)
                    )
        for pattern in _IMP.get(lang, []):
            for m in pattern.finditer(source):
                if m.group(1) not in result.imports:
                    result.imports.append(m.group(1))
        return result


class _LineIndex:
    def __init__(self, source: str):
        self._offsets = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                self._offsets.append(i + 1)

    def at(self, pos: int) -> int:
        lo, hi = 0, len(self._offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._offsets[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1
