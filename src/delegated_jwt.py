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
from .oauth_flow import exchange_on_behalf_of, fetch_openid_metadata

logger = get_logger()

_jwks_uri_cache: str | None = None
_token_endpoint_cache: str | None = None
_jwk_client: PyJWKClient | None = None
_jwk_client_uri: str | None = None

# (subject, scope_str) -> (access_token, expires_at_unix)
_obo_cache: dict[tuple[str, str], tuple[str, float]] = {}
_obo_lock = asyncio.Lock()


async def resolve_jwks_uri() -> str:
    """Return JWKS URI from config or OpenID discovery."""
    global _jwks_uri_cache, _token_endpoint_cache
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
    te = str(meta.get("token_endpoint", "")).strip()
    if te:
        _token_endpoint_cache = te
    return uri


async def resolve_token_endpoint() -> str:
    """Return OAuth token_endpoint from cache or OpenID discovery (one GET)."""
    global _token_endpoint_cache, _jwks_uri_cache
    if _token_endpoint_cache:
        return _token_endpoint_cache
    async with aiohttp.ClientSession() as session:
        meta = await fetch_openid_metadata(session, Config.OPENID_CONFIGURATION_URL)
    te = str(meta.get("token_endpoint", "")).strip()
    if not te:
        raise AuthError("OpenID metadata missing token_endpoint")
    ju = str(meta.get("jwks_uri", "")).strip()
    if ju and not Config.ACCUBID_DELEGATED_JWKS_URL.strip() and not _jwks_uri_cache:
        _jwks_uri_cache = ju
    _token_endpoint_cache = te
    return te


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


def _scopes_for_diagnostics(payload: dict[str, Any]) -> list[str]:
    """Scopes list for logs/errors: mirrors JWT `scope` plus implicit `openid` when OIDC identity is present.

    Trimble often omits the literal ``openid`` token from the ``scope`` claim even when the client
    requested OpenID; if ``iss`` and ``sub`` are present, prepend ``openid`` so diagnostics match
    Studio UI / expected ``openid accubid_agentic_ai`` style.
    """
    scopes = list(_scope_claims(payload))
    if payload.get("iss") and payload.get("sub") and "openid" not in scopes:
        scopes.insert(0, "openid")
    return scopes


def safe_claims_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Non-sensitive JWT claims for diagnostics (no raw token)."""
    out: dict[str, Any] = {}
    for key in ("azp", "sub", "account_id", "data_region", "iss", "exp"):
        val = payload.get(key)
        if val is not None and val != "":
            out[key] = val
    scopes = _scopes_for_diagnostics(payload)
    if scopes:
        out["scopes"] = scopes
    return out


def safe_claims_unverified(token: str) -> dict[str, Any]:
    """Extract safe claims when ACCUBID_DELEGATED_VERIFY=false (signature not validated)."""
    try:
        payload = jwt.decode(
            token,
            algorithms=["RS256"],
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
        if isinstance(payload, dict):
            return safe_claims_from_payload(payload)
    except jwt.PyJWTError:
        logger.debug("safe_claims_unverified decode failed", exc_info=True)
    return {}


def _missing_required_scopes(required: list[str], payload: dict[str, Any]) -> list[str]:
    """Return required scope names not satisfied by the token.

    The literal ``openid`` string is often omitted from the ``scope`` claim even when the client
    requested the OpenID scope (Agent Studio still shows ``openid`` in the UI). If ``openid`` is
    required but absent from ``scope``, treat it as satisfied when standard OIDC identity
    claims are present (``iss`` and ``sub``).
    """
    have = set(_scope_claims(payload))
    missing: list[str] = []
    for name in required:
        if name in have:
            continue
        if name == "openid" and payload.get("iss") and payload.get("sub"):
            continue
        missing.append(name)
    return missing


def verify_jwt_sync(token: str, *, jwks_uri: str) -> dict[str, Any]:
    """Validate signature, issuer, audience, exp; check required scopes. Returns safe claim dict."""
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
        missing = _missing_required_scopes(required, payload)
        if missing:
            raise AuthError(
                "Delegated JWT missing required scopes",
                details={"missing_scopes": missing, "has_scopes": sorted(have)},
            )

    return safe_claims_from_payload(payload)


async def verify_delegated_jwt(token: str) -> dict[str, Any]:
    """Async wrapper (JWKS fetch + CPU-bound verify in thread). Returns safe claim dict."""
    jwks_uri = await resolve_jwks_uri()
    return await asyncio.to_thread(verify_jwt_sync, token, jwks_uri=jwks_uri)


def _obo_cache_ttl_seconds(expires_in: int | None) -> float:
    if expires_in and expires_in > 0:
        return max(float(expires_in) - 60.0, 30.0)
    return float(Config.ACCUBID_TOKEN_TTL_SECONDS)


async def resolve_outbound_access_token() -> tuple[str | None, dict[str, Any] | None]:
    """Return (bearer token for Accubid API, safe actor JWT claims) or (None, None) for server OAuth.

    In ``delegated`` / ``hybrid`` (with actor), the first value is usually an access token from
    Trimble token exchange so ``azp`` matches this MCP's ``CLIENT_ID`` (subscribed app), not the
    Agent Studio client. ``claims`` always reflects the inbound actor for diagnostics.

    If ``hybrid`` and ``ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH`` is true, returns ``(None, claims)``
    and Accubid HTTP uses the server OAuth token instead of OBO.
    """
    mode = Config.ACCUBID_AUTH_MODE
    if mode == "server":
        return None, None

    raw = extract_bearer_raw_from_request()
    if mode == "hybrid" and not raw:
        return None, None
    if mode == "delegated" and not raw:
        raise AuthError(
            "ACCUBID_AUTH_MODE=delegated requires an actor token on each MCP request. "
            "Use streamable HTTP from Trimble Agent Studio with On behalf of actor token, "
            "or switch to ACCUBID_AUTH_MODE=hybrid with server OAuth fallback.",
        )

    assert raw is not None
    if Config.ACCUBID_DELEGATED_VERIFY:
        claims = await verify_delegated_jwt(raw)
    else:
        claims = safe_claims_unverified(raw)

    if mode == "hybrid" and Config.hybrid_accubid_use_server_oauth():
        logger.info(
            "ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH enabled: skipping On-Behalf-Of exchange; "
            "Accubid requests use server OAuth (CLIENT_ID / ACCUBID_OAUTH_GRANT). "
            "Actor JWT is validated for diagnostics only."
        )
        return None, claims

    scope_str = " ".join(Config.accubid_scopes())
    sub = str(claims.get("sub") or "").strip() or "__missing_sub__"
    cache_key = (sub, scope_str)

    now = time.time()
    async with _obo_lock:
        hit = _obo_cache.get(cache_key)
        if hit and hit[1] > now:
            return hit[0], claims

    token_endpoint = await resolve_token_endpoint()
    async with aiohttp.ClientSession() as session:
        token_data = await exchange_on_behalf_of(
            session,
            token_endpoint=token_endpoint,
            client_id=Config.CLIENT_ID,
            client_secret=Config.CLIENT_SECRET,
            subject_token=raw,
            scope=scope_str,
            resource=Config.token_exchange_resource(),
        )

    access = str(token_data.get("access_token") or token_data.get("AccessToken") or "").strip()
    if not access:
        raise AuthError(
            "Token exchange returned no access_token",
            details={"keys": list(token_data.keys())},
        )

    ei = token_data.get("expires_in")
    expires_in_i = int(ei) if isinstance(ei, (int, float)) else None
    ttl = _obo_cache_ttl_seconds(expires_in_i)
    expires_at = time.time() + ttl

    async with _obo_lock:
        now2 = time.time()
        hit2 = _obo_cache.get(cache_key)
        if hit2 and hit2[1] > now2:
            return hit2[0], claims
        _obo_cache[cache_key] = (access, expires_at)

    return access, claims


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
