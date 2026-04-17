"""Per-MCP-request access token for delegated (Agent Studio actor) auth."""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_access_token: ContextVar[str | None] = ContextVar("accubid_request_access_token", default=None)


def get_request_access_token() -> str | None:
    return _request_access_token.get()


def set_request_access_token(token: str | None) -> Token[str | None]:
    return _request_access_token.set(token)


def reset_request_access_token(ctx: Token[str | None]) -> None:
    _request_access_token.reset(ctx)
