"""Optional Prometheus metrics helpers."""

from __future__ import annotations

from typing import Any, Callable

_PROMETHEUS_AVAILABLE = True
_GEN_LATEST: Callable[[], bytes]

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
    )
    from prometheus_client import (
        generate_latest as _GEN_LATEST,
    )
except ImportError:  # pragma: no cover - optional dependency
    _PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    def _GEN_LATEST() -> bytes:
        return b""


_TOOL_CALLS: Any = (
    Counter(
        "accubid_mcp_tool_calls_total",
        "Total tool calls by tool name and status",
        ["tool", "status"],
    )
    if _PROMETHEUS_AVAILABLE
    else None
)
_TOOL_DURATION_SECONDS: Any = (
    Histogram(
        "accubid_mcp_tool_duration_seconds",
        "Tool execution duration in seconds",
        ["tool"],
    )
    if _PROMETHEUS_AVAILABLE
    else None
)


def metrics_enabled() -> bool:
    return _TOOL_CALLS is not None and _TOOL_DURATION_SECONDS is not None


def observe_tool_success(tool_name: str, duration_seconds: float) -> None:
    if not metrics_enabled():
        return
    _TOOL_CALLS.labels(tool=tool_name, status="success").inc()
    _TOOL_DURATION_SECONDS.labels(tool=tool_name).observe(duration_seconds)


def observe_tool_failure(tool_name: str, duration_seconds: float) -> None:
    if not metrics_enabled():
        return
    _TOOL_CALLS.labels(tool=tool_name, status="error").inc()
    _TOOL_DURATION_SECONDS.labels(tool=tool_name).observe(duration_seconds)


def render_metrics() -> tuple[bytes, str]:
    return _GEN_LATEST(), CONTENT_TYPE_LATEST
