"""Bounded-concurrency helpers for composed tools."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from .config import Config

T = TypeVar("T")


async def run_bounded(coros: list[Awaitable[T]], *, limit: int | None = None) -> list[T]:
    """Execute awaitables with a bounded level of concurrency."""
    max_concurrency = max(1, limit or Config.ACCUBID_COMPOSED_TOOL_CONCURRENCY)
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(*(_run(coro) for coro in coros))
