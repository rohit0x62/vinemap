"""Vinemap Teams — shared graph server API."""

import os
import sys
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

# Allow running from teams/ with engine on path
_ENGINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "engine"))
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)

from vinemap.graph.model import CodeGraph
from vinemap.license import parse_and_verify_key

from server.auth import require_actor
from server.federated import cross_repo_rank
from server.store import TeamsStore

DATA_DIR = os.environ.get("VINEMAP_TEAMS_DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "teams.db")
MAX_SEATS = int(os.environ.get("VINEMAP_TEAMS_MAX_SEATS", "50"))
ORG_ID = os.environ.get("VINEMAP_TEAMS_ORG_ID", "default")

app = FastAPI(title="Vinemap Teams", version="0.1.0")
store = TeamsStore(DB_PATH)


class IndexBody(BaseModel):
    name: str
    graph: dict


class DecisionBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    repo_id: Optional[str] = None


class LicenseVerifyBody(BaseModel):
    key: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **store.stats()}


@app.get("/v1/repos")
def list_repos(_actor: str = Depends(require_actor)) -> dict:
    return {"repos": store.list_repos()}


@app.post("/v1/repos/{repo_id}/index")
def index_repo(
    repo_id: str,
    body: IndexBody,
    actor: str = Depends(require_actor),
) -> dict:
    if not body.graph.get("files"):
        raise HTTPException(status_code=400, detail="graph.files required")
    store.upsert_repo(repo_id, body.name or repo_id, body.graph)
    store.audit(actor, "index", f"repo={repo_id} name={body.name}")
    stats = CodeGraph.from_dict(body.graph).stats()
    return {"repo_id": repo_id, "stats": stats}


@app.get("/v1/repos/{repo_id}")
def get_repo(repo_id: str, _actor: str = Depends(require_actor)) -> dict:
    repo = store.get_repo(repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")
    return repo


@app.get("/v1/retrieve")
def retrieve(
    query: str,
    k: int = 10,
    repo_id: Optional[str] = None,
    _actor: str = Depends(require_actor),
) -> dict:
    if not query.strip():
        raise HTTPException(status_code=400, detail="query required")
    if repo_id:
        repo = store.get_repo(repo_id)
        if repo is None:
            raise HTTPException(status_code=404, detail="repo not found")
        graphs = [(repo_id, CodeGraph.from_dict(repo["graph"]))]
    else:
        graphs = [
            (g["id"], CodeGraph.from_dict(g["graph"])) for g in store.all_graphs()
        ]
    if not graphs:
        return {"query": query, "results": [], "message": "no indexed repos"}
    results = cross_repo_rank(graphs, query.strip(), k=min(k, 50))
    store.audit(_actor, "retrieve", f"query={query[:80]!r} hits={len(results)}")
    return {"query": query, "results": results}


@app.post("/v1/decisions")
def post_decision(body: DecisionBody, actor: str = Depends(require_actor)) -> dict:
    did = store.add_decision(actor, body.text, repo_id=body.repo_id)
    store.audit(actor, "decision", f"id={did} repo={body.repo_id}")
    return {"id": did, "author": actor, "text": body.text}


@app.get("/v1/decisions")
def get_decisions(
    repo_id: Optional[str] = None,
    limit: int = 50,
    _actor: str = Depends(require_actor),
) -> dict:
    return {"decisions": store.list_decisions(repo_id=repo_id, limit=min(limit, 200))}


@app.post("/v1/license/verify")
def verify_license(body: LicenseVerifyBody) -> dict:
    try:
        info = parse_and_verify_key(body.key.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if info.tier != "teams":
        raise HTTPException(status_code=403, detail="Teams license required")
    email = info.subject or "unknown"
    if store.count_seats(ORG_ID) >= MAX_SEATS and email:
        # allow re-verify for existing seat
        pass
    if info.subject:
        store.add_seat(info.subject.lower(), ORG_ID)
    store.audit(email, "license_verify", f"tier={info.tier}")
    return {
        "valid": True,
        "tier": info.tier,
        "subject": info.subject,
        "seats_used": store.count_seats(ORG_ID),
        "seats_max": MAX_SEATS,
    }


@app.get("/v1/audit")
def audit_log(limit: int = 100, _actor: str = Depends(require_actor)) -> dict:
    return {"events": store.recent_audit(limit=min(limit, 500))}


@app.get("/v1/stats")
def team_stats(_actor: str = Depends(require_actor)) -> dict:
    return store.stats()
