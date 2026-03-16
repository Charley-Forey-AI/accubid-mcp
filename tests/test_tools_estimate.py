from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from src.registry import HANDLER_REGISTRY
from src.tools import estimate

DB_TOKEN = "123e4567-e89b-12d3-a456-426614174000"
PROJECT_ID = "223e4567-e89b-12d3-a456-426614174000"


@pytest.mark.asyncio
async def test_list_estimates_calls_client_and_wraps_response() -> None:
    mcp = FastMCP("test-estimate")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_estimates.return_value = [{"estimateID": "E1"}]
    estimate.set_client(mock_client)
    estimate.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["list_estimates"].fn(DB_TOKEN, PROJECT_ID)
    assert result["ok"] is True
    assert result["data"]["estimates"] == [{"estimateID": "E1"}]
    assert result["data"]["pagination"]["total_count"] == 1
    mock_client.get_estimates.assert_awaited_once_with(
        DB_TOKEN,
        PROJECT_ID,
        search=None,
        sort_by=None,
        sort_direction="asc",
    )


@pytest.mark.asyncio
async def test_get_estimates_by_due_date_normalizes_iso_format() -> None:
    mcp = FastMCP("test-estimate-validation")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_estimates_by_due_date.return_value = []
    estimate.set_client(mock_client)
    estimate.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["get_estimates_by_due_date"].fn(DB_TOKEN, "2026-01-01", "20260102")
    assert result["ok"] is True
    mock_client.get_estimates_by_due_date.assert_awaited_once_with(
        DB_TOKEN,
        "20260101",
        "20260102",
    )
