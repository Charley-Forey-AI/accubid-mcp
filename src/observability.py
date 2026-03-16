"""Request context and response envelope helpers."""

from __future__ import annotations

import contextvars
import uuid
from typing import Any

from .errors import AccubidMcpError

_request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="",
)


def ensure_request_id() -> str:
    """Get or create request id for the current context."""
    request_id = _request_id_context.get()
    if request_id:
        return request_id
    request_id = str(uuid.uuid4())
    _request_id_context.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """Force request id for the current context."""
    _request_id_context.set(request_id.strip())


def get_request_id() -> str:
    """Return request id or empty string when unavailable."""
    return _request_id_context.get()


def clear_request_id() -> None:
    """Clear request id after one operation completes."""
    _request_id_context.set("")


def success_response(data: Any) -> dict[str, Any]:
    """Return a successful, consistent tool response envelope."""
    return {
        "ok": True,
        "request_id": ensure_request_id(),
        "data": data,
    }


def error_response(error: AccubidMcpError) -> dict[str, Any]:
    """Return a failure, consistent tool response envelope."""
    payload: dict[str, Any] = {
        "ok": False,
        "request_id": ensure_request_id(),
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.details:
        payload["error"]["details"] = error.details
    return payload
