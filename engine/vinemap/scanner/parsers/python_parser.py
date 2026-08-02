"""Precise Python parser built on the stdlib `ast` module."""

import ast
from typing import List, Optional

from vinemap.scanner.parsers.base import ParsedFile, Symbol


def _signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = []
        for a in node.args.args:
            ann = f": {ast.unparse(a.annotation)}" if a.annotation else ""
            args.append(f"{a.arg}{ann}")
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)}){ret}"
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(b) for b in node.bases)
        return f"class {node.name}({bases})" if bases else f"class {node.name}"
    return ""


def _call_names(node: ast.AST) -> List[str]:
    names = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            if isinstance(fn, ast.Name):
                names.append(fn.id)
            elif isinstance(fn, ast.Attribute):
                names.append(fn.attr)
    # dedupe, keep order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out[:32]


class PythonParser:
    """Extracts functions, classes, methods, imports, and call edges."""

    languages = ["python"]
    extensions = [".py"]

    def parse(self, path: str, source: str) -> ParsedFile:
        result = ParsedFile(path=path, language="python", line_count=source.count("\n") + 1)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return result

        result.module_docstring = (ast.get_docstring(tree) or "")[:500]

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                result.imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                result.imports.append(("." * node.level) + node.module)

        def visit(node: ast.AST, parent: Optional[str]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(child, ast.ClassDef) else (
                        "method" if parent else "function"
                    )
                    result.symbols.append(
                        Symbol(
                            name=child.name,
                            kind=kind,
                            line_start=child.lineno,
                            line_end=getattr(child, "end_lineno", child.lineno),
                            signature=_signature(child),
                            docstring=(ast.get_docstring(child) or "")[:200],
                            calls=_call_names(child) if kind != "class" else [],
                            parent=parent,
                        )
                    )
                    visit(child, child.name)
                else:
                    visit(child, parent)

        visit(tree, None)
        return result
