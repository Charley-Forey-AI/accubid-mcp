"""Trimble Identity auth provider for Accubid MCP."""

import asyncio
import time
from typing import Optional

from trimble.id import ClientCredentialTokenProvider, OpenIdEndpointProvider

from .config import Config
from .errors import AuthError
from .log_config import get_logger

logger = get_logger()


class AccubidAuth:
    """Client-credentials token provider with lightweight in-memory cache."""

    def __init__(self) -> None:
        endpoint_provider = OpenIdEndpointProvider(Config.OPENID_CONFIGURATION_URL)
        self._token_provider = ClientCredentialTokenProvider(
            endpoint_provider, Config.CLIENT_ID, Config.CLIENT_SECRET
        ).with_scopes(Config.accubid_scopes())
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

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
        # Some SDKs return typed objects.
        token = str(getattr(token_obj, "access_token", None) or getattr(token_obj, "token", "")).strip()
        expires_in = getattr(token_obj, "expires_in", None)
        if isinstance(expires_in, (int, float)):
            return token, int(expires_in)
        return token, None

    async def get_access_token(self) -> str:
        """Return a valid access token."""
        if self._is_token_valid():
            return self._access_token or ""

        async with self._lock:
            if self._is_token_valid():
                return self._access_token or ""

            token_obj = await self._token_provider.retrieve_token()
            token, expires_in = self._extract_token_and_expiry(token_obj)
            if not token:
                raise AuthError("Failed to retrieve access token from Trimble Identity")

            self._access_token = token
            if expires_in and expires_in > 0:
                self._expires_at = time.time() + expires_in
            else:
                # SDK often returns token string only. Use configured TTL fallback.
                logger.debug("Token expiry metadata unavailable; using ACCUBID_TOKEN_TTL_SECONDS fallback")
                self._expires_at = time.time() + Config.ACCUBID_TOKEN_TTL_SECONDS
            return token
