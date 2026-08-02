import pytest

from vinemap.scanner.parsers.treesitter_parser import TreeSitterParser, treesitter_available


pytestmark = pytest.mark.skipif(
    not treesitter_available(),
    reason="tree-sitter extra not installed (pip install vinemap[treesitter])",
)


@pytest.fixture
def ts_parser():
    return TreeSitterParser()


def test_typescript_extracts_symbols_and_imports(ts_parser):
    source = """
import { login } from "./app/auth";

export function handleLogin(req: Request): Response {
    const ok = login(req);
    return new Response("ok");
}

export class ApiServer {
    start() {
        this.listen();
    }
}
"""
    pf = ts_parser.parse("web.ts", source)
    names = {s.name for s in pf.symbols}
    assert "handleLogin" in names
    assert "ApiServer" in names
    assert "start" in names
    assert "./app/auth" in pf.imports

    handle = next(s for s in pf.symbols if s.name == "handleLogin")
    assert "login" in handle.calls


def test_go_extracts_functions_and_imports(ts_parser):
    source = """
package main

import (
    "fmt"
    "os"
)

func greet(name string) string {
    fmt.Println(name)
    return name
}

type Server struct{}

func (s *Server) Run() {
    os.Exit(0)
}
"""
    pf = ts_parser.parse("main.go", source)
    names = {s.name for s in pf.symbols}
    assert "greet" in names
    assert "Server" in names
    assert "Run" in names
    assert "fmt" in pf.imports or any("fmt" in imp for imp in pf.imports)

    greet = next(s for s in pf.symbols if s.name == "greet")
    assert "Println" in greet.calls


def test_rust_extracts_functions(ts_parser):
    source = """
use std::collections::HashMap;

pub fn build_index() -> HashMap<String, i32> {
    let mut m = HashMap::new();
    m.insert(String::from("a"), 1);
    m
}

pub struct Graph {}
"""
    pf = ts_parser.parse("lib.rs", source)
    names = {s.name for s in pf.symbols}
    assert "build_index" in names
    assert "Graph" in names


def test_registry_prefers_treesitter():
    from vinemap.scanner.parsers import get_parser, using_treesitter

    assert using_treesitter() is True
    parser = get_parser("web.ts")
    assert repr(parser) == "TreeSitterParser()"
