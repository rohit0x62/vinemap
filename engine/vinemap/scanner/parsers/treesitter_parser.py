"""Precise multi-language parser via tree-sitter (optional extra).

Install: pip install vinemap[treesitter]

Uses tree-sitter-language-pack for grammars. Falls back to RegexParser
when tree-sitter is not installed or a grammar is unavailable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from vinemap.scanner.parsers.base import ParsedFile, Symbol

_EXT_TO_LANG: Dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
}

# tree-sitter node types treated as functions/methods per language
_FN_TYPES: Dict[str, Set[str]] = {
    "javascript": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "arrow_function",
    },
    "typescript": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "arrow_function",
    },
    "go": {"function_declaration", "method_declaration"},
    "java": {"method_declaration", "constructor_declaration"},
    "rust": {"function_item"},
    "ruby": {"method", "singleton_method"},
    "python": {"function_definition"},
    "csharp": {"method_declaration", "constructor_declaration"},
    "cpp": {"function_definition"},
    "c": {"function_definition"},
    "php": {"function_definition", "method_declaration"},
    "kotlin": {"function_declaration"},
    "swift": {"function_declaration"},
}

_CLS_TYPES: Dict[str, Set[str]] = {
    "javascript": {"class_declaration", "class"},
    "typescript": {"class_declaration", "class"},
    "go": {"type_declaration"},
    "java": {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"},
    "rust": {"struct_item", "enum_item", "trait_item", "impl_item"},
    "ruby": {"class", "module"},
    "csharp": {"class_declaration", "struct_declaration", "interface_declaration", "record_declaration"},
    "cpp": {"class_specifier", "struct_specifier"},
    "php": {"class_declaration", "interface_declaration", "trait_declaration"},
    "kotlin": {"class_declaration", "object_declaration"},
    "swift": {"class_declaration", "struct_declaration", "enum_declaration", "protocol_declaration"},
}


def treesitter_available() -> bool:
    try:
        from tree_sitter_language_pack import get_parser  # noqa: F401

        return True
    except ImportError:
        return False


def _line_1based(row: int) -> int:
    return row + 1


class TreeSitterParser:
    """Tree-sitter parser covering the same extensions as RegexParser."""

    extensions = list(_EXT_TO_LANG.keys())
    languages = sorted(set(_EXT_TO_LANG.values()))

    def __init__(self) -> None:
        from tree_sitter_language_pack import get_parser

        self._get_parser = get_parser
        self._cache: Dict[str, object] = {}

    def _parser_for(self, lang: str):
        if lang not in self._cache:
            self._cache[lang] = self._get_parser(lang)
        return self._cache[lang]

    def parse(self, path: str, source: str) -> ParsedFile:
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = _EXT_TO_LANG.get(ext, "unknown")
        result = ParsedFile(path=path, language=lang, line_count=source.count("\n") + 1)
        if lang == "unknown":
            return result

        try:
            parser = self._parser_for(lang)
            tree = parser.parse(source.encode("utf-8", errors="replace"))
        except Exception:
            return result

        root = tree.root_node
        self._extract_imports(root, source, lang, result)
        self._extract_symbols(root, source, lang, result)
        return result

    def _extract_imports(self, node, source: str, lang: str, result: ParsedFile) -> None:
        if lang == "go" and node.type == "import_spec":
            for child in node.children:
                if child.type == "interpreted_string_literal":
                    mod = source[child.start_byte : child.end_byte].strip('"')
                    if mod and mod not in result.imports:
                        result.imports.append(mod)
            return
        if node.type in ("import_statement", "import_declaration", "use_declaration", "preproc_include"):
            spec = source[node.start_byte : node.end_byte].strip()
            if lang == "go" and node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec_list":
                        for spec_node in child.children:
                            if spec_node.type == "import_spec":
                                self._extract_imports(spec_node, source, lang, result)
                return
            if lang == "rust" and node.type == "use_declaration":
                txt = source[node.start_byte : node.end_byte].replace("use ", "").split(";")[0].strip()
                if txt:
                    result.imports.append(txt)
                return
            # JS/TS/Java style — grab quoted module paths
            for child in node.children:
                if child.type == "string":
                    mod = source[child.start_byte : child.end_byte].strip("'\"")
                    if mod and mod not in result.imports:
                        result.imports.append(mod)
            if lang == "java" and node.type == "import_declaration":
                txt = source[node.start_byte : node.end_byte].replace("import ", "").replace(";", "").strip()
                if txt:
                    result.imports.append(txt)
            return
        for i in range(node.child_count):
            self._extract_imports(node.child(i), source, lang, result)

    def _extract_symbols(self, root, source: str, lang: str, result: ParsedFile) -> None:
        fn_types = _FN_TYPES.get(lang, set())
        cls_types = _CLS_TYPES.get(lang, set())

        def walk(node, parent: Optional[str]) -> None:
            ntype = node.type
            if ntype in fn_types or ntype in cls_types:
                name = _symbol_name(node, source, lang, ntype)
                if name:
                    kind = "class" if ntype in cls_types else ("method" if parent else "function")
                    if ntype in cls_types and lang == "go":
                        kind = "class"
                    sig = source[node.start_byte : node.end_byte].split("{")[0].strip()[:200]
                    if not sig:
                        sig = source[node.start_byte : min(node.end_byte, node.start_byte + 120)].strip()
                    result.symbols.append(
                        Symbol(
                            name=name,
                            kind=kind,
                            line_start=_line_1based(node.start_point.row),
                            line_end=_line_1based(node.end_point.row),
                            signature=sig,
                            calls=_calls_in_node(node, source) if kind != "class" else [],
                            parent=parent,
                        )
                    )
                    if ntype in cls_types:
                        for i in range(node.child_count):
                            walk(node.child(i), name)
                        return
            for i in range(node.child_count):
                walk(node.child(i), parent)

        walk(root, None)

    def __repr__(self) -> str:
        return "TreeSitterParser()"


def _symbol_name(node, source: str, lang: str, ntype: str) -> Optional[str]:
    if lang == "go" and ntype == "method_declaration":
        for child in node.children:
            if child.type == "field_identifier":
                return source[child.start_byte : child.end_byte]
    # Prefer named identifier children
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier", "field_identifier", "name"):
            return source[child.start_byte : child.end_byte]
    if lang == "go" and ntype == "function_declaration":
        for child in node.children:
            if child.type == "identifier":
                return source[child.start_byte : child.end_byte]
    if lang == "go" and ntype == "type_declaration":
        for child in node.children:
            if child.type == "type_spec":
                for sub in child.children:
                    if sub.type == "type_identifier":
                        return source[sub.start_byte : sub.end_byte]
    return None


def _calls_in_node(node, source: str) -> List[str]:
    names: List[str] = []
    seen: Set[str] = set()

    def walk(n) -> None:
        if n.type == "call_expression":
            fn = n.child_by_field_name("function") if hasattr(n, "child_by_field_name") else None
            if fn is None and n.child_count:
                fn = n.children[0]
            if fn is not None:
                if fn.type == "identifier":
                    name = source[fn.start_byte : fn.end_byte]
                elif fn.type in ("field_expression", "selector_expression"):
                    name = source[fn.start_byte : fn.end_byte].split(".")[-1]
                elif fn.type == "scoped_identifier":
                    name = source[fn.start_byte : fn.end_byte].split("::")[-1]
                else:
                    name = None
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
        for i in range(n.child_count):
            walk(n.child(i))

    walk(node)
    return names[:32]
