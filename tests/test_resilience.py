import asyncio

import pytest

from src.errors import CircuitOpenError
from src.resilience import CircuitBreaker, RateLimiter


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_blocks_requests() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30)
    await breaker.on_failure()
    await breaker.on_failure()

    assert breaker.is_open is True
    with pytest.raises(CircuitOpenError):
        await breaker.before_request()


@pytest.mark.asyncio
async def test_circuit_breaker_transitions_half_open_after_cooldown() -> None:
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
    await breaker.on_failure()
    assert breaker.is_open is True

    await asyncio.sleep(0.02)
    await breaker.before_request()  # half-open probe is allowed
    await breaker.on_success()
    assert breaker.is_open is False


@pytest.mark.asyncio
async def test_rate_limiter_waits_when_tokens_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RateLimiter(requests_per_second=1)
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.resilience.asyncio.sleep", fake_sleep)

    await limiter.acquire()
    await limiter.acquire()

    assert sleep_calls
    assert sleep_calls[0] > 0


@pytest.mark.asyncio
async def test_rate_limiter_disabled_for_zero_rps(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RateLimiter(requests_per_second=0)
    sleep_called = False

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_called
        sleep_called = True

    monkeypatch.setattr("src.resilience.asyncio.sleep", fake_sleep)
    await limiter.acquire()
    assert sleep_called is False
