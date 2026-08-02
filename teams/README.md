# Vinemap Teams — Shared Graph Server (Phase 5)

Self-hosted infrastructure for engineering teams. Centralizes code graphs across repos,
enables cross-repo retrieval, shared decision memory, seat licensing, and audit logs.

## Quick start

```bash
cd teams
cp .env.example .env   # set VINEMAP_TEAMS_API_TOKEN
docker compose up -d
curl http://localhost:7430/health
```

## CLI workflow

```bash
# Requires Teams license: vinemap license activate VMP1...
vinemap index .
vinemap teams connect http://localhost:7430 --token dev-token-change-me .
vinemap teams push .
vinemap teams retrieve "where do we validate JWTs"
vinemap teams decisions --text "Auth middleware validates JWT in gateway" .
vinemap teams sync .
vinemap teams status .
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server health + counts |
| GET | `/v1/repos` | List indexed repos |
| POST | `/v1/repos/{id}/index` | Upload graph JSON |
| GET | `/v1/retrieve?query=` | Cross-repo ranked search |
| POST | `/v1/decisions` | Record shared decision |
| GET | `/v1/decisions` | List decisions (with author) |
| POST | `/v1/license/verify` | Validate Teams seat |
| GET | `/v1/audit` | Audit log |
| GET | `/v1/stats` | Org statistics |

## Authentication

1. **API token** — set `VINEMAP_TEAMS_API_TOKEN`; clients pass `Authorization: Bearer <token>`
2. **OIDC SSO** — set `OIDC_ISSUER` + `OIDC_AUDIENCE`; clients pass OIDC JWT as Bearer
3. **Dev mode** — if neither is set, accepts `X-Vinemap-Actor` header

## Architecture

```
Developer machines                    Your VPC / Docker
┌─────────────────┐                  ┌──────────────────────────┐
│ vinemap index   │                  │  Vinemap Teams Server    │
│ vinemap teams   │ ─── push ──────► │  SQLite: graphs,         │
│   push/sync     │ ◄── retrieve ─── │    decisions, audit,     │
└─────────────────┘                  │    seats                 │
                                     └──────────────────────────┘
```

Cross-repo retrieval ranks files independently per repo, merges scores globally,
and returns `{repo_id, path, score}` hits — e.g. find JWT validation across
`gateway`, `auth-service`, and `mobile-api` in one query.

## Seat management

`POST /v1/license/verify` accepts a Teams `VMP1` license key, validates Ed25519
signature (same format as Pro), and registers the seat up to `VINEMAP_TEAMS_MAX_SEATS`.

Issue keys:

```bash
export VINEMAP_LICENSE_PRIVATE_KEY=<hex>
python engine/tools/issue_license.py --tier teams --days 365 --subject user@company.com
```

## Deploy to production

- Run behind HTTPS reverse proxy (nginx, Caddy, Cloudflare Tunnel)
- Use strong `VINEMAP_TEAMS_API_TOKEN` or OIDC
- Mount persistent volume at `/data`
- Set `VINEMAP_TEAMS_ORG_ID` per customer for multi-tenant hosting

See [docs/MOAT.md](../docs/MOAT.md) for strategy.
