"""Per-MCP-request context: actor Bearer from HTTP (streamable-http) and outbound token for diagnostics."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_actor_token: ContextVar[str | None] = ContextVar("accubid_actor_token", default=None)
_outbound_token: ContextVar[str | None] = ContextVar("accubid_outbound_token", default=None)

HEADER_AUTHORIZATION = "Authorization"


def ensure_request_context_populated_from_http() -> None:
    """Populate actor token from FastMCP HTTP headers when available."""
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers(include_all=True)
        if headers:
            populate_from_headers(headers)
    except Exception:
        pass


def populate_from_headers(headers: dict[str, Any]) -> None:
    """Extract Bearer token from Authorization header (case-insensitive)."""
    if not headers:
        return
    h = {k.lower(): v for k, v in headers.items() if v}
    auth = h.get(HEADER_AUTHORIZATION.lower())
    if auth and isinstance(auth, str) and auth.strip().lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            _actor_token.set(token)


def get_actor_token() -> str | None:
    try:
        return _actor_token.get()
    except LookupError:
        return None


def get_request_outbound_token() -> str | None:
    """Exchanged access token last set by AccubidClient for 900909 diagnostics."""
    try:
        return _outbound_token.get()
    except LookupError:
        return None


def set_request_outbound_token(token: str | None) -> Token[str | None]:
    return _outbound_token.set(token)


def reset_request_outbound_token(ctx: Token[str | None]) -> None:
    _outbound_token.reset(ctx)
