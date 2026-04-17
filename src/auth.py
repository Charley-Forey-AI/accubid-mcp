"""Trimble Identity auth for Accubid MCP (client credentials or authorization code + PKCE)."""

import asyncio
import time
from typing import Optional

import aiohttp
from trimble.id import ClientCredentialTokenProvider, OpenIdEndpointProvider

from .config import Config
from .errors import AuthError
from .log_config import get_logger
from .oauth_flow import (
    fetch_openid_metadata,
    read_token_file,
    refresh_access_token,
    write_token_file,
)

logger = get_logger()


class AccubidAuth:
    """Token provider: client_credentials via trimble-id, or authorization_code via token file + refresh."""

    def __init__(self) -> None:
        self._auth_mode = Config.ACCUBID_AUTH_MODE
        grant = Config.ACCUBID_OAUTH_GRANT
        self._grant = grant
        self._cc_provider: ClientCredentialTokenProvider | None = None

        if self._auth_mode == "delegated":
            # Outbound Accubid calls use per-request actor JWT (see request_context + delegated_jwt).
            pass
        elif self._auth_mode in ("server", "hybrid"):
            if grant == "client_credentials":
                endpoint_provider = OpenIdEndpointProvider(Config.OPENID_CONFIGURATION_URL)
                self._cc_provider = ClientCredentialTokenProvider(
                    endpoint_provider, Config.CLIENT_ID, Config.CLIENT_SECRET
                ).with_scopes(Config.accubid_scopes())
            elif grant == "authorization_code":
                pass
            else:
                raise AuthError(
                    "Invalid ACCUBID_OAUTH_GRANT",
                    details={"value": grant, "allowed": ["client_credentials", "authorization_code"]},
                )
        else:
            raise AuthError(
                "Invalid ACCUBID_AUTH_MODE",
                details={"value": self._auth_mode, "allowed": ["server", "delegated", "hybrid"]},
            )

        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._refresh_token: Optional[str] = None
        self._lock = asyncio.Lock()
        self._token_endpoint: Optional[str] = None

    def _is_token_valid(self) -> bool:
        now = time.time()
        return (
            bool(self._access_token)
            and self._expires_at > 0
            and now < (self._expires_at - Config.ACCUBID_TOKEN_REFRESH_BUFFER_SECONDS)
        )

    @staticmethod
    def _extract_token_and_expiry(token_obj: object) -> tuple[str, int | None]:
        """Extract token and expiry in seconds from common token payload shapes."""
        if isinstance(token_obj, str):
            return token_obj, None
        if isinstance(token_obj, dict):
            token = str(token_obj.get("access_token") or token_obj.get("token") or "").strip()
            expires_in = token_obj.get("expires_in")
            if isinstance(expires_in, (int, float)):
                return token, int(expires_in)
            return token, None
        token = str(getattr(token_obj, "access_token", None) or getattr(token_obj, "token", "")).strip()
        expires_in = getattr(token_obj, "expires_in", None)
        if isinstance(expires_in, (int, float)):
            return token, int(expires_in)
        return token, None

    async def _ensure_token_endpoint(self, session: aiohttp.ClientSession) -> str:
        if self._token_endpoint:
            return self._token_endpoint
        meta = await fetch_openid_metadata(session, Config.OPENID_CONFIGURATION_URL)
        endpoint = str(meta.get("token_endpoint", "")).strip()
        if not endpoint:
            raise AuthError("OpenID metadata missing token_endpoint")
        self._token_endpoint = endpoint
        return endpoint

    async def _get_access_token_client_credentials(self) -> str:
        assert self._cc_provider is not None
        token_obj = await self._cc_provider.retrieve_token()
        token, expires_in = self._extract_token_and_expiry(token_obj)
        if not token:
            raise AuthError("Failed to retrieve access token from Trimble Identity")
        self._access_token = token
        if expires_in and expires_in > 0:
            self._expires_at = time.time() + expires_in
        else:
            logger.debug("Token expiry metadata unavailable; using ACCUBID_TOKEN_TTL_SECONDS fallback")
            self._expires_at = time.time() + Config.ACCUBID_TOKEN_TTL_SECONDS
        return token

    async def _get_access_token_authorization_code(self) -> str:
        path = Config.oauth_token_path_resolved()
        scope_str = " ".join(Config.accubid_scopes())
        now = time.time()

        data = read_token_file(path)
        if data:
            access = str(data.get("access_token", "")).strip()
            refresh = data.get("refresh_token")
            refresh_s = str(refresh).strip() if refresh else None
            exp = data.get("expires_at")
            try:
                exp_f = float(exp) if exp is not None else 0.0
            except (TypeError, ValueError):
                exp_f = 0.0

            if access and exp_f > now + Config.ACCUBID_TOKEN_REFRESH_BUFFER_SECONDS:
                self._access_token = access
                self._expires_at = exp_f
                self._refresh_token = refresh_s
                return access

            if refresh_s:
                async with aiohttp.ClientSession() as session:
                    token_endpoint = await self._ensure_token_endpoint(session)
                    payload = await refresh_access_token(
                        session,
                        token_endpoint=token_endpoint,
                        client_id=Config.CLIENT_ID,
                        client_secret=Config.CLIENT_SECRET,
                        refresh_token=refresh_s,
                        scope=scope_str,
                    )
                access_new = str(payload.get("access_token", "")).strip()
                if not access_new:
                    raise AuthError("Refresh response missing access_token")
                new_refresh = payload.get("refresh_token")
                new_refresh_s = str(new_refresh).strip() if new_refresh else refresh_s
                ei = payload.get("expires_in")
                ei_i = int(ei) if isinstance(ei, (int, float)) else None
                write_token_file(
                    path,
                    access_token=access_new,
                    refresh_token=new_refresh_s,
                    expires_in=ei_i,
                    fallback_ttl_seconds=Config.ACCUBID_TOKEN_TTL_SECONDS,
                )
                ttl = float(ei_i) if ei_i else float(Config.ACCUBID_TOKEN_TTL_SECONDS)
                self._access_token = access_new
                self._expires_at = time.time() + ttl
                self._refresh_token = new_refresh_s
                return access_new

        raise AuthError(
            "No valid user tokens. Run: accubid-mcp-oauth-login (with browser login), "
            "or set ACCUBID_OAUTH_GRANT=client_credentials.",
            details={"token_file": str(path)},
        )

    async def get_access_token(self) -> str:
        """Return a valid access token."""
        if self._auth_mode == "delegated":
            raise AuthError(
                "ACCUBID_AUTH_MODE=delegated uses the actor token from each MCP request only. "
                "It was not available when resolving the Accubid API Authorization header.",
                details={"hint": "Use Agent Studio streamable HTTP with On behalf of actor token."},
            )

        if self._grant == "client_credentials":
            if self._is_token_valid():
                return self._access_token or ""
            async with self._lock:
                if self._is_token_valid():
                    return self._access_token or ""
                return await self._get_access_token_client_credentials()

        # authorization_code
        if self._is_token_valid():
            return self._access_token or ""
        async with self._lock:
            if self._is_token_valid():
                return self._access_token or ""
            return await self._get_access_token_authorization_code()
