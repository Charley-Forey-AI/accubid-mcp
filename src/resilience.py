"""Resilience primitives for API access."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import CircuitOpenError


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float = 0.0
    is_open: bool = False
    half_open_trial: bool = False


class CircuitBreaker:
    """Simple in-memory circuit breaker."""

    def __init__(
        self,
        *,
        failure_threshold: int,
        cooldown_seconds: float,
        state_file: str | None = None,
    ) -> None:
        self._failure_threshold = max(1, failure_threshold)
        self._cooldown_seconds = max(0.001, cooldown_seconds)
        self._state_file = state_file.strip() if state_file else ""
        self._state = CircuitState()
        self._lock = asyncio.Lock()
        self._load_state()

    def _load_state(self) -> None:
        if not self._state_file:
            return
        path = Path(self._state_file)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._state = CircuitState(
                failures=int(data.get("failures", 0)),
                opened_at=float(data.get("opened_at", 0.0)),
                is_open=bool(data.get("is_open", False)),
                half_open_trial=bool(data.get("half_open_trial", False)),
            )
        except Exception:
            self._state = CircuitState()

    def _persist_state(self) -> None:
        if not self._state_file:
            return
        path = Path(self._state_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "failures": self._state.failures,
                        "opened_at": self._state.opened_at,
                        "is_open": self._state.is_open,
                        "half_open_trial": self._state.half_open_trial,
                    }
                ),
                encoding="utf-8",
            )
        except Exception:
            # State persistence should never block request flow.
            pass

    async def before_request(self) -> None:
        async with self._lock:
            if not self._state.is_open:
                return
            elapsed = time.monotonic() - self._state.opened_at
            if elapsed >= self._cooldown_seconds:
                # Permit one probe request in half-open mode.
                self._state.half_open_trial = True
                return
            raise CircuitOpenError(
                "Accubid API circuit breaker is open; requests are temporarily blocked.",
                details={"retry_after_seconds": round(self._cooldown_seconds - elapsed, 2)},
            )

    async def on_success(self) -> None:
        async with self._lock:
            self._state = CircuitState()
            self._persist_state()

    async def on_failure(self) -> None:
        async with self._lock:
            self._state.failures += 1
            if self._state.half_open_trial or self._state.failures >= self._failure_threshold:
                self._state.is_open = True
                self._state.opened_at = time.monotonic()
                self._state.half_open_trial = False
            self._persist_state()

    @property
    def is_open(self) -> bool:
        return self._state.is_open


class RateLimiter:
    """Token-bucket limiter with optional async wait."""

    def __init__(self, *, requests_per_second: float) -> None:
        self._rps = max(0.0, requests_per_second)
        self._capacity = max(1.0, self._rps) if self._rps > 0 else 0.0
        self._tokens = self._capacity
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._rps <= 0:
            return
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = max(0.0, now - self._last)
                self._last = now
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rps)
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait_seconds = (1.0 - self._tokens) / self._rps
                await asyncio.sleep(wait_seconds)
