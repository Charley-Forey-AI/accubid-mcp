"""Shared error types and conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AccubidMcpError(Exception):
    """Base application error with stable error code."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ValidationError(AccubidMcpError):
    """Error raised for invalid tool input values."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="validation_error", message=message, details=details or {})


class AuthError(AccubidMcpError):
    """Error raised when identity token acquisition fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="auth_failed", message=message, details=details or {})


class ApiError(AccubidMcpError):
    """Error raised for Accubid API failures."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = dict(details or {})
        if status_code is not None:
            full_details["status_code"] = status_code
        super().__init__(code="api_error", message=message, details=full_details)
        self.status_code = status_code


class DependencyCheckError(AccubidMcpError):
    """Error raised when dependency checks fail."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="dependency_unhealthy", message=message, details=details or {})


class CircuitOpenError(AccubidMcpError):
    """Error raised when the API circuit breaker is open."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="circuit_open", message=message, details=details or {})


def to_mcp_error(exc: Exception) -> AccubidMcpError:
    """Map arbitrary exceptions to a stable MCP error payload."""
    if isinstance(exc, AccubidMcpError):
        return exc
    return AccubidMcpError(code="internal_error", message=str(exc), details={})
