import os
from pathlib import Path

import pytest

from vinemap.agents.claude import setup_claude
from vinemap.agents.codex import setup_codex
from vinemap.agents.copilot import setup_copilot
from vinemap.agents.cursor import setup_cursor
from vinemap.agents.gemini import setup_gemini
from vinemap.agents.opencode import setup_opencode
from vinemap.guardrails import Guardrails
from vinemap.inject import extract_query_from_prompt
from vinemap.rank.bm25 import bm25_scores


def test_extract_query_from_prompt():
    assert "auth" in extract_query_from_prompt("how does\nauth work")


def test_bm25_scores_non_empty(project):
    from vinemap.graph.model import CodeGraph
    from vinemap.scanner.walker import scan_project

    files, _, _ = scan_project(project)
    graph = CodeGraph.build(files)
    scores = bm25_scores(graph, "password login hash")
    assert scores.get("app/auth.py", 0) > 0


def test_guardrails_read_budget():
    g = Guardrails(read_budget=2)
    ok, _ = g.check_read("a.py")
    assert ok
    g.record_read("a.py")
    g.record_read("b.py")
    ok, msg = g.check_read("c.py")
    assert not ok and "budget" in (msg or "").lower()


def test_setup_cursor_writes_rules(project):
    wrote, _msg = setup_cursor(project)
    assert wrote
    assert (Path(project) / ".cursor" / "rules" / "vinemap.mdc").is_file()


def test_setup_claude_writes_hooks(project):
    wrote, _msg = setup_claude(project)
    assert wrote
    hook = Path(project) / ".claude" / "hooks" / "vinemap-inject.sh"
    session = Path(project) / ".claude" / "hooks" / "vinemap-session-end.sh"
    assert hook.is_file()
    assert session.is_file()
    assert os.access(hook, os.X_OK)


def test_setup_gemini_writes_instructions(project):
    wrote, _msg = setup_gemini(project)
    assert wrote
    assert (Path(project) / ".gemini" / "GEMINI.md").is_file()


def test_setup_copilot_writes_instructions(project):
    wrote, _msg = setup_copilot(project)
    assert wrote
    assert (Path(project) / ".github" / "copilot-instructions.md").is_file()


def test_setup_opencode_writes_rules(project):
    wrote, _msg = setup_opencode(project)
    assert wrote
    assert (Path(project) / ".opencode" / "rules" / "vinemap.md").is_file()


def test_guardrails_grep_hint():
    g = Guardrails(read_budget=12)
    assert g.grep_hint() is None
    for i in range(4):
        g.record_read(f"f{i}.py")
    hint = g.grep_hint()
    assert hint and "graph_retrieve" in hint
