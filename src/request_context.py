"""Per-MCP-request access token and actor JWT claims for delegated (Agent Studio) auth."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_request_access_token: ContextVar[str | None] = ContextVar("accubid_request_access_token", default=None)
_request_token_claims: ContextVar[dict[str, Any] | None] = ContextVar(
    "accubid_request_token_claims", default=None
)


def get_request_access_token() -> str | None:
    return _request_access_token.get()


def set_request_access_token(token: str | None) -> Token[str | None]:
    return _request_access_token.set(token)


def reset_request_access_token(ctx: Token[str | None]) -> None:
    _request_access_token.reset(ctx)


def get_request_token_claims() -> dict[str, Any] | None:
    """Safe Trimble JWT claims for the current request (azp, sub, account_id, scopes, …)."""
    return _request_token_claims.get()


def set_request_token_claims(claims: dict[str, Any] | None) -> Token[dict[str, Any] | None]:
    return _request_token_claims.set(claims)


def reset_request_token_claims(ctx: Token[dict[str, Any] | None]) -> None:
    _request_token_claims.reset(ctx)
