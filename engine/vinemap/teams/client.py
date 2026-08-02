"""HTTP client for Vinemap Teams shared graph server."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class TeamsClient:
    def __init__(self, base_url: str, token: Optional[str] = None, actor: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.environ.get("VINEMAP_TEAMS_TOKEN", "")
        self.actor = actor or os.environ.get("VINEMAP_TEAMS_ACTOR", "")

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if self.actor:
            req.add_header("X-Vinemap-Actor", self.actor)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Teams API {exc.code}: {detail}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def list_repos(self) -> List[dict]:
        return self._request("GET", "/v1/repos")["repos"]

    def push_graph(self, repo_id: str, name: str, graph: dict) -> dict:
        return self._request("POST", f"/v1/repos/{urllib.parse.quote(repo_id)}/index", {
            "name": name,
            "graph": graph,
        })

    def retrieve(self, query: str, k: int = 10, repo_id: Optional[str] = None) -> dict:
        params = urllib.parse.urlencode({"query": query, "k": k, **({"repo_id": repo_id} if repo_id else {})})
        return self._request("GET", f"/v1/retrieve?{params}")

    def post_decision(self, text: str, repo_id: Optional[str] = None) -> dict:
        return self._request("POST", "/v1/decisions", {"text": text, "repo_id": repo_id})

    def list_decisions(self, repo_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        q = urllib.parse.urlencode({"limit": limit, **({"repo_id": repo_id} if repo_id else {})})
        return self._request("GET", f"/v1/decisions?{q}")["decisions"]

    def verify_license(self, key: str) -> dict:
        return self._request("POST", "/v1/license/verify", {"key": key})
