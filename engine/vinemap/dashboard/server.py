"""Local web dashboard for token savings and session stats."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlparse

from vinemap.graph.store import load_graph
from vinemap.license import current_tier, license_status_text
from vinemap.memory.session import SessionMemory


def _html(root: str) -> str:
    graph = load_graph(root)
    memory = SessionMemory(root)
    stats = graph.stats() if graph else {"files": 0, "symbols": 0, "import_edges": 0}
    weights = memory.file_weights()
    touches = sorted(weights.items(), key=lambda kv: -kv[1])[:15]
    decisions = memory.recent_decisions(20)
    tier = current_tier()
    tokens_est = memory.total_tokens_saved()

    rows = "".join(
        f"<tr><td>{p}</td><td>{w:.2f}</td></tr>" for p, w in touches
    ) or "<tr><td colspan=2>No touches yet</td></tr>"
    decs = "".join(f"<li>{d}</li>" for d in decisions) or "<li>None yet</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Vinemap Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 880px; margin: 2rem auto; padding: 0 1rem; background: #0d1117; color: #e6edf3; }}
    h1 {{ color: #3fb950; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; }}
    .val {{ font-size: 1.8rem; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ text-align: left; padding: 0.4rem; border-bottom: 1px solid #30363d; }}
    .tier {{ text-transform: uppercase; color: #58a6ff; }}
  </style>
</head>
<body>
  <h1>Vinemap</h1>
  <p class="tier">{tier} · {root}</p>
  <div class="grid">
    <div class="card"><div class="val">{stats.get('files', 0)}</div>files indexed</div>
    <div class="card"><div class="val">{stats.get('symbols', 0)}</div>symbols</div>
    <div class="card"><div class="val">{len(memory.events)}</div>session touches</div>
    <div class="card"><div class="val">~{tokens_est:,}</div>tokens via graph</div>
  </div>
  <h2>Most touched files</h2>
  <table><tr><th>Path</th><th>Weight</th></tr>{rows}</table>
  <h2>Session decisions</h2>
  <ul>{decs}</ul>
  <p><small>{license_status_text().replace(chr(10), ' · ')}</small></p>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    root: str = "."

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            body = _html(self.root).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/api/stats":
            graph = load_graph(self.root)
            memory = SessionMemory(self.root)
            data = {
                "tier": current_tier(),
                "graph": graph.stats() if graph else {},
                "session": {
                    "touches": len(memory.events),
                    "decisions": len(memory.decisions),
                    "tokens_estimated": memory.total_tokens_saved(),
                },
            }
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def serve_dashboard(root: str, port: int = 7423, host: str = "127.0.0.1") -> None:
    root = os.path.abspath(root)
    DashboardHandler.root = root
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Vinemap dashboard → http://{host}:{port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
