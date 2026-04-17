"""Validate Trimble Identity JWTs for delegated (on-behalf-of) MCP auth."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp
import jwt
from jwt import PyJWKClient

from .config import Config
from .errors import AuthError
from .log_config import get_logger

logger = get_logger()

_jwks_uri_cache: str | None = None
_jwk_client: PyJWKClient | None = None
_jwk_client_uri: str | None = None


async def resolve_jwks_uri() -> str:
    """Return JWKS URI from config or OpenID discovery."""
    global _jwks_uri_cache
    explicit = Config.ACCUBID_DELEGATED_JWKS_URL.strip()
    if explicit:
        return explicit
    if _jwks_uri_cache:
        return _jwks_uri_cache
    async with aiohttp.ClientSession() as session:
        async with session.get(Config.OPENID_CONFIGURATION_URL) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise AuthError(
                    "Failed to load OpenID configuration for JWKS",
                    details={"status": resp.status, "body": text[:512]},
                )
            meta = await resp.json()
    uri = str(meta.get("jwks_uri", "")).strip()
    if not uri:
        raise AuthError("OpenID metadata missing jwks_uri; set ACCUBID_DELEGATED_JWKS_URL")
    _jwks_uri_cache = uri
    return uri


def _get_jwk_client(jwks_uri: str) -> PyJWKClient:
    global _jwk_client, _jwk_client_uri
    if _jwk_client is None or _jwk_client_uri != jwks_uri:
        _jwk_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=300)
        _jwk_client_uri = jwks_uri
    return _jwk_client


def _decode_options() -> dict[str, Any]:
    aud = Config.delegated_audience_list()
    return {"verify_aud": bool(aud)}


def _audience_for_jwt() -> str | list[str] | None:
    auds = Config.delegated_audience_list()
    if not auds:
        return None
    if len(auds) == 1:
        return auds[0]
    return auds


def _scope_claims(payload: dict[str, Any]) -> list[str]:
    sc = payload.get("scope")
    if isinstance(sc, str):
        return [p for p in sc.split() if p]
    if isinstance(sc, list):
        return [str(x) for x in sc if str(x).strip()]
    return []


def verify_jwt_sync(token: str, *, jwks_uri: str) -> None:
    """Validate signature, issuer, audience, exp; check required scopes."""
    client = _get_jwk_client(jwks_uri)
    signing_key = client.get_signing_key_from_jwt(token)
    issuer = Config.ACCUBID_DELEGATED_ISSUER.rstrip("/")
    audience = _audience_for_jwt()
    decode_kw: dict[str, Any] = {
        "algorithms": ["RS256"],
        "issuer": issuer,
        "leeway": Config.ACCUBID_DELEGATED_JWT_LEEWAY_SECONDS,
        "options": _decode_options(),
    }
    if audience is not None:
        decode_kw["audience"] = audience

    try:
        payload = jwt.decode(token, signing_key.key, **decode_kw)
    except jwt.PyJWTError as exc:
        raise AuthError("Delegated JWT validation failed", details={"cause": str(exc)}) from exc

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        raise AuthError("Delegated JWT expired")

    required = Config.delegated_required_scopes_list()
    if required:
        have = set(_scope_claims(payload))
        missing = [s for s in required if s not in have]
        if missing:
            raise AuthError(
                "Delegated JWT missing required scopes",
                details={"missing_scopes": missing, "has_scopes": sorted(have)},
            )


async def verify_delegated_jwt(token: str) -> None:
    """Async wrapper (JWKS fetch + CPU-bound verify in thread)."""
    jwks_uri = await resolve_jwks_uri()
    await asyncio.to_thread(verify_jwt_sync, token, jwks_uri=jwks_uri)


async def resolve_outbound_access_token() -> str | None:
    """Bearer string for Accubid API calls, or None to fall back to server OAuth (hybrid only)."""
    mode = Config.ACCUBID_AUTH_MODE
    if mode == "server":
        return None

    raw = extract_bearer_raw_from_request()
    if mode == "hybrid" and not raw:
        return None
    if mode == "delegated" and not raw:
        raise AuthError(
            "ACCUBID_AUTH_MODE=delegated requires an actor token on each MCP request. "
            "Use streamable HTTP from Trimble Agent Studio with On behalf of actor token, "
            "or switch to ACCUBID_AUTH_MODE=hybrid with server OAuth fallback.",
        )

    assert raw is not None
    if Config.ACCUBID_DELEGATED_VERIFY:
        await verify_delegated_jwt(raw)
    return raw


def extract_bearer_raw_from_request() -> str | None:
    """Prefer FastMCP/MCP verified access token, then Authorization header."""
    try:
        from fastmcp.server.dependencies import get_access_token as fm_get_access_token
    except ImportError:
        fm_get_access_token = None  # type: ignore[assignment]

    if fm_get_access_token is not None:
        try:
            at = fm_get_access_token()
            if at is not None and getattr(at, "token", None):
                raw = str(at.token).strip()
                if raw:
                    return raw
        except Exception:
            logger.debug("get_access_token() unavailable or failed", exc_info=True)

    try:
        from fastmcp.server.dependencies import get_http_request
    except ImportError:
        get_http_request = None  # type: ignore[assignment]

    if get_http_request is not None:
        try:
            req = get_http_request()
            h = req.headers.get("authorization") or req.headers.get("Authorization") or ""
            if h.lower().startswith("bearer "):
                return h[7:].strip()
        except RuntimeError:
            pass
    return None
