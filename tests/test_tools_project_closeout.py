from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from src.registry import HANDLER_REGISTRY
from src.tools import closeout, project

DB_TOKEN = "123e4567-e89b-12d3-a456-426614174000"
BID_SUMMARY_ID = "323e4567-e89b-12d3-a456-426614174000"
VIEW_ID = "423e4567-e89b-12d3-a456-426614174000"


@pytest.mark.asyncio
async def test_list_projects_calls_client() -> None:
    mcp = FastMCP("test-project")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_projects.return_value = [{"projectID": "P1"}, {"projectID": "P2"}]
    project.set_client(mock_client)
    project.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["list_projects"].fn(DB_TOKEN, page_index=0, page_size=1)
    assert result["ok"] is True
    assert result["data"]["projects"] == [{"projectID": "P1"}]
    assert result["data"]["pagination"]["total_count"] == 2
    assert result["data"]["pagination"]["has_next_page"] is True
    mock_client.get_projects.assert_awaited_once_with(
        DB_TOKEN,
        search=None,
        sort_by=None,
        sort_direction="asc",
    )


@pytest.mark.asyncio
async def test_closeout_get_bid_breakdown_rejects_negative_page_index() -> None:
    mcp = FastMCP("test-closeout")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    closeout.set_client(mock_client)
    closeout.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["get_bid_breakdown"].fn(
        DB_TOKEN,
        BID_SUMMARY_ID,
        VIEW_ID,
        page_index=-1,
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "validation_error"
    mock_client.get_bid_breakdown.assert_not_called()


@pytest.mark.asyncio
async def test_closeout_get_bid_breakdown_normalizes_pagination_shape() -> None:
    mcp = FastMCP("test-closeout-pagination")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_bid_breakdown.return_value = {
        "pageIndex": 0,
        "pageSize": 2,
        "totalItems": 3,
        "items": [{"id": "1"}, {"id": "2"}],
    }
    closeout.set_client(mock_client)
    closeout.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["get_bid_breakdown"].fn(DB_TOKEN, BID_SUMMARY_ID, VIEW_ID, page_index=0)
    assert result["ok"] is True
    assert result["data"]["items"] == [{"id": "1"}, {"id": "2"}]
    assert result["data"]["pagination"]["total_count"] == 3
    assert result["data"]["pagination"]["has_next_page"] is True
