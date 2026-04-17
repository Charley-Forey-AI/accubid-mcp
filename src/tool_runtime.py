"""Shared runtime wrapper for tool execution."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextvars import Token
from typing import Any

from .config import Config
from .delegated_jwt import resolve_outbound_access_token
from .errors import to_mcp_error
from .log_config import get_logger
from .metrics import observe_tool_failure, observe_tool_success
from .observability import clear_request_id, ensure_request_id, error_response, success_response
from .request_context import (
    reset_request_access_token,
    reset_request_token_claims,
    set_request_access_token,
    set_request_token_claims,
)
from .response_normalization import normalize_keys_to_snake_case

logger = get_logger()


async def execute_tool(
    tool_name: str,
    operation: Callable[[], Awaitable[Any]],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a tool with common validation/error/logging behavior."""
    request_id = ensure_request_id()
    start = time.perf_counter()
    context_payload = context or {}
    reset_token: Token[str | None] | None = None
    reset_claims: Token[dict[str, Any] | None] | None = None
    try:
        if Config.ACCUBID_AUTH_MODE in ("delegated", "hybrid"):
            outbound, actor_claims = await resolve_outbound_access_token()
            if outbound:
                reset_token = set_request_access_token(outbound)
            if actor_claims is not None:
                reset_claims = set_request_token_claims(actor_claims)
        result = await operation()
        if Config.ACCUBID_RESPONSE_SNAKE_CASE:
            result = normalize_keys_to_snake_case(result)
        duration_seconds = time.perf_counter() - start
        duration_ms = int(duration_seconds * 1000)
        logger.info(
            "tool_success tool=%s request_id=%s duration_ms=%s context=%s",
            tool_name,
            request_id,
            duration_ms,
            context_payload,
        )
        observe_tool_success(tool_name, duration_seconds)
        return success_response(result)
    except Exception as exc:
        duration_seconds = time.perf_counter() - start
        duration_ms = int(duration_seconds * 1000)
        app_error = to_mcp_error(exc)
        logger.exception(
            "tool_failed tool=%s request_id=%s duration_ms=%s code=%s context=%s",
            tool_name,
            request_id,
            duration_ms,
            app_error.code,
            context_payload,
        )
        observe_tool_failure(tool_name, duration_seconds)
        return error_response(app_error)
    finally:
        if reset_claims is not None:
            reset_request_token_claims(reset_claims)
        if reset_token is not None:
            reset_request_access_token(reset_token)
        clear_request_id()
