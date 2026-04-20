"""Trimble Identity on-behalf-of (RFC 8693) token exchange for Accubid Anywhere."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession

from .config import Config
from .errors import AuthError
from .request_context import ensure_request_context_populated_from_http, get_actor_token

# Seconds before cached exchanged token expiry to refresh (avoid edge-of-expiry 401s).
_EXCHANGE_CACHE_SKEW_SECONDS = 30


def _looks_like_jwt(token: str) -> bool:
    """True if token looks like a JWT (three segments, header has alg)."""
    if not token or not isinstance(token, str):
        return False
    parts = token.strip().split(".")
    if len(parts) != 3:
        return False
    try:
        segment = parts[0].strip()
        pad = 4 - (len(segment) % 4)
        if pad != 4:
            segment += "=" * pad
        decoded = base64.urlsafe_b64decode(segment)
        header = json.loads(decoded.decode("utf-8"))
        return isinstance(header, dict) and "alg" in header
    except Exception:
        return False


async def _fetch_openid_metadata(session: ClientSession, openid_configuration_url: str) -> dict[str, Any]:
    async with session.get(openid_configuration_url) as response:
        if response.status != 200:
            text = await response.text()
            raise AuthError(
                "Failed to load OpenID configuration",
                details={"status": response.status, "body": text[:512]},
            )
        return await response.json()


def _cache_key(actor_token: str, scope_str: str) -> str:
    h = hashlib.sha256()
    h.update(actor_token.encode("utf-8"))
    h.update(b"\n")
    h.update(scope_str.encode("utf-8"))
    return h.hexdigest()


class AccubidAuth:
    """Exchange Agent Studio actor Bearer for an Accubid-scoped access token (per request)."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[str, float]] = {}
        self._token_endpoint: str | None = None
        self._lock = asyncio.Lock()

    async def _ensure_token_endpoint(self, session: ClientSession) -> str:
        if self._token_endpoint:
            return self._token_endpoint
        meta = await _fetch_openid_metadata(session, Config.OPENID_CONFIGURATION_URL)
        endpoint = str(meta.get("token_endpoint", "")).strip()
        if not endpoint:
            raise AuthError("OpenID metadata missing token_endpoint")
        self._token_endpoint = endpoint
        return endpoint

    def _get_cached(self, key: str) -> str | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        token, expires_at = entry
        if expires_at <= time.time():
            self._cache.pop(key, None)
            return None
        return token

    def _set_cached(self, key: str, access_token: str, ttl_seconds: float) -> None:
        ttl = max(ttl_seconds - _EXCHANGE_CACHE_SKEW_SECONDS, 30.0)
        self._cache[key] = (access_token, time.time() + ttl)

    async def _exchange_once(
        self,
        session: ClientSession,
        *,
        token_endpoint: str,
        subject_token: str,
        scope_str: str,
        subject_token_type: str,
    ) -> tuple[int, str]:
        credentials = f"{Config.CLIENT_ID}:{Config.CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        form: dict[str, str] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "scope": scope_str,
        }
        body = urlencode(form)
        async with session.post(token_endpoint, data=body, headers=headers) as response:
            return response.status, await response.text()

    def _parse_success(self, response_text: str) -> tuple[str, float]:
        try:
            token_data: dict[str, Any] = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise AuthError(
                "Token exchange response was not valid JSON",
                details={"body": response_text[:2048]},
            ) from exc
        if "error" in token_data:
            desc = str(
                token_data.get("error_description") or token_data.get("error") or "Unknown error"
            )
            raise AuthError(
                "Token exchange error",
                details={"error": token_data.get("error"), "error_description": desc[:2048]},
            )
        access = token_data.get("access_token") or token_data.get("AccessToken")
        if not access or not str(access).strip():
            raise AuthError(
                "Token exchange response missing access_token",
                details={"keys": list(token_data.keys())},
            )
        token = str(access).strip().replace("\n", "").replace("\r", "").replace("\t", "")
        ei = token_data.get("expires_in")
        ttl: float
        if isinstance(ei, (int, float)) and ei > 0:
            ttl = float(ei)
        else:
            ttl = 3300.0
        return token, ttl

    async def _exchange(self, actor_token: str, scope_str: str) -> tuple[str, float]:
        use_jwt_type = _looks_like_jwt(actor_token)
        subject_token_type = (
            "urn:ietf:params:oauth:token-type:jwt"
            if use_jwt_type
            else "urn:ietf:params:oauth:token-type:access_token"
        )

        async with ClientSession() as session:
            token_endpoint = await self._ensure_token_endpoint(session)

            status, response_text = await self._exchange_once(
                session,
                token_endpoint=token_endpoint,
                subject_token=actor_token,
                scope_str=scope_str,
                subject_token_type=subject_token_type,
            )
            if status == 200:
                return self._parse_success(response_text)

            if (
                status == 400
                and "not supported" in response_text.lower()
                and not use_jwt_type
                and _looks_like_jwt(actor_token)
            ):
                status, response_text = await self._exchange_once(
                    session,
                    token_endpoint=token_endpoint,
                    subject_token=actor_token,
                    scope_str=scope_str,
                    subject_token_type="urn:ietf:params:oauth:token-type:jwt",
                )
                if status == 200:
                    return self._parse_success(response_text)

            msg_lower = response_text.lower()
            if "signature verification failed" in msg_lower:
                raise AuthError(
                    "On-behalf-of token exchange failed: JWT signature verification failed. "
                    "Ensure OPENID_CONFIGURATION_URL matches the environment that issued the token.",
                    details={"status": status, "body": response_text[:2048]},
                )
            if "intended audience" in msg_lower or "not the intended audience" in msg_lower:
                raise AuthError(
                    "On-behalf-of token exchange failed: caller is not the intended audience of the subject token. "
                    "Ensure CLIENT_ID matches the MCP application registered for token exchange in "
                    "Trimble Developer Console.",
                    details={"status": status, "body": response_text[:2048]},
                )
            if status == 400 and ("unsupported_grant_type" in msg_lower or "invalid_grant" in msg_lower):
                raise AuthError(
                    "On-behalf-of token exchange rejected by Trimble Identity. "
                    "Enable the token exchange (On-Behalf-Of) grant for this application in the "
                    "Trimble Developer Console and ensure ACCUBID_SCOPE includes scopes your app may request.",
                    details={"status": status, "body": response_text[:2048]},
                )
            raise AuthError(
                f"On-behalf-of token exchange failed with HTTP {status}",
                details={"status": status, "body": response_text[:2048]},
            )

    async def get_access_token(self) -> str:
        """Return an Accubid-ready access token (exchanged from the incoming Authorization Bearer)."""
        ensure_request_context_populated_from_http()
        actor = get_actor_token()
        if not actor or not actor.strip():
            raise AuthError(
                "No Authorization: Bearer on MCP request. "
                "Use streamable HTTP from Agent Studio with an On behalf of actor token.",
                details={"hint": "Each MCP request must include Authorization: Bearer <actor JWT>."},
            )
        actor = actor.strip()
        scope_parts = Config.accubid_scopes()
        scope_str = " ".join(scope_parts)
        key = _cache_key(actor, scope_str)

        cached = self._get_cached(key)
        if cached:
            return cached

        async with self._lock:
            cached = self._get_cached(key)
            if cached:
                return cached
            exchanged, ttl = await self._exchange(actor, scope_str)
            self._set_cached(key, exchanged, ttl)
            return exchanged
