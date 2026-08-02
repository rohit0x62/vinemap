"""Parser interfaces and data model shared by all language parsers."""

from dataclasses import dataclass, field
from typing import List, Optional, Protocol


@dataclass
class Symbol:
    """A named code entity: function, class, method, or constant."""

    name: str
    kind: str  # "function" | "class" | "method" | "constant"
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    calls: List[str] = field(default_factory=list)
    parent: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "calls": self.calls,
            "parent": self.parent,
        }

    @staticmethod
    def from_dict(d: dict) -> "Symbol":
        return Symbol(
            name=d["name"],
            kind=d["kind"],
            line_start=d["line_start"],
            line_end=d["line_end"],
            signature=d.get("signature", ""),
            docstring=d.get("docstring", ""),
            calls=d.get("calls", []),
            parent=d.get("parent"),
        )


@dataclass
class ParsedFile:
    """Result of parsing one source file."""

    path: str  # relative to project root, posix-style
    language: str
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)  # raw import specifiers
    line_count: int = 0
    content_hash: str = ""
    module_docstring: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports,
            "line_count": self.line_count,
            "content_hash": self.content_hash,
            "module_docstring": self.module_docstring,
        }

    @staticmethod
    def from_dict(d: dict) -> "ParsedFile":
        return ParsedFile(
            path=d["path"],
            language=d["language"],
            symbols=[Symbol.from_dict(s) for s in d.get("symbols", [])],
            imports=d.get("imports", []),
            line_count=d.get("line_count", 0),
            content_hash=d.get("content_hash", ""),
            module_docstring=d.get("module_docstring", ""),
        )


class Parser(Protocol):
    """A language parser turns source text into a ParsedFile."""

    languages: List[str]
    extensions: List[str]

    def parse(self, path: str, source: str) -> ParsedFile: ...
