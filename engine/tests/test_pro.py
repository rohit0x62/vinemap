import textwrap

from vinemap.graph.model import CodeGraph
from vinemap.pro.audit import audit_symbol
from vinemap.pro.coverage import coverage_score
from vinemap.pro.diagnose import diagnose_stack_trace
from vinemap.pro.health import find_circular_imports, find_dead_exports
from vinemap.rank.ranker import rank_files
from vinemap.scanner.walker import scan_project


def _build(root):
    files, _, _ = scan_project(root)
    return CodeGraph.build(files)


def test_diagnose_finds_frame_and_blast(project):
    graph = _build(project)
    trace = textwrap.dedent('''
        Traceback (most recent call last):
          File "app/auth.py", line 8, in login
            return user and hash_password(password) == user["password"]
        KeyError: 'password'
    ''')
    report = diagnose_stack_trace(graph, trace)
    assert report["frames_in_index"] >= 1
    assert report["root_candidates"][0]["path"] == "app/auth.py"
    assert "app/db.py" in report["blast_radius"] or "app/main.py" in report["blast_radius"]


def test_health_detects_cycle(tmp_path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")
    graph = _build(str(tmp_path))
    cycles = find_circular_imports(graph)
    assert cycles and {"a.py", "b.py"} <= set(cycles[0])


def test_audit_finds_symbol(project):
    graph = _build(project)
    hits = audit_symbol(graph, project, "login")
    paths = {h["path"] for h in hits}
    assert "app/auth.py" in paths


def test_coverage_score(project):
    graph = _build(project)
    ranked = rank_files(graph, "password hashing")
    paths = [p for p, _ in ranked]
    score, inc, uni = coverage_score(graph, "password hashing", paths[:1])
    assert 0 <= score <= 100
    assert inc <= uni


def test_dead_exports_heuristic(project):
    graph = _build(project)
    dead = find_dead_exports(graph)
    # db.get_user is used; hash_password should not be flagged as dead if referenced
    names = {d["symbol"] for d in dead}
    assert "get_user" not in names
