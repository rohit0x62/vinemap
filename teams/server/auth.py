"""Authentication for Teams server: API token + optional OIDC JWT."""

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from fastapi import HTTPException, Request


def _api_token() -> str:
    return os.environ.get("VINEMAP_TEAMS_API_TOKEN", "").strip()


def _oidc_issuer() -> str:
    return os.environ.get("OIDC_ISSUER", "").strip().rstrip("/")


def _jwks_cache() -> dict:
    issuer = _oidc_issuer()
    if not issuer:
        return {}
    if not hasattr(_jwks_cache, "_data"):
        try:
            with urllib.request.urlopen(f"{issuer}/.well-known/openid-configuration", timeout=5) as r:
                meta = json.load(r)
            jwks_uri = meta.get("jwks_uri", "")
            with urllib.request.urlopen(jwks_uri, timeout=5) as r:
                _jwks_cache._data = json.load(r)  # type: ignore[attr-defined]
        except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
            _jwks_cache._data = {}  # type: ignore[attr-defined]
    return _jwks_cache._data  # type: ignore[attr-defined]


def verify_bearer_token(token: str) -> Optional[str]:
    """Return actor email/subject if token is valid."""
    if not token:
        return None
    expected = _api_token()
    if expected and token == expected:
        return "api-token"

    issuer = _oidc_issuer()
    if not issuer:
        return None

    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError:
        return None

    try:
        jwks = _jwks_cache()
        if not jwks.get("keys"):
            return None
        client = PyJWKClient(f"{issuer}/.well-known/jwks.json")
        signing = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing.key,
            algorithms=["RS256", "ES256"],
            audience=os.environ.get("OIDC_AUDIENCE") or None,
            issuer=issuer,
            options={"verify_aud": bool(os.environ.get("OIDC_AUDIENCE"))},
        )
        return str(payload.get("email") or payload.get("sub") or "oidc-user")
    except Exception:
        return None


async def require_actor(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        actor = verify_bearer_token(auth[7:].strip())
        if actor:
            return actor
    # Dev mode: allow unauthenticated if no token configured
    if not _api_token() and not _oidc_issuer():
        return request.headers.get("X-Vinemap-Actor", "anonymous")
    raise HTTPException(status_code=401, detail="Unauthorized — provide Bearer token or OIDC JWT")
