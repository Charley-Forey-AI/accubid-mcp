from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from src.registry import HANDLER_REGISTRY
from src.tools import changeorder, workflows

DB_TOKEN = "123e4567-e89b-12d3-a456-426614174000"
PROJECT_ID = "223e4567-e89b-12d3-a456-426614174000"
CONTRACT_ID = "323e4567-e89b-12d3-a456-426614174000"
ESTIMATE_ID = "423e4567-e89b-12d3-a456-426614174000"
BID_SUMMARY_ID = "523e4567-e89b-12d3-a456-426614174000"
VIEW_ID = "623e4567-e89b-12d3-a456-426614174000"


@pytest.mark.asyncio
async def test_list_contracts_applies_status_filter() -> None:
    mcp = FastMCP("test-changeorder")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_contracts.return_value = [
        {"contractID": CONTRACT_ID, "status": "Open"},
        {"contractID": "723e4567-e89b-12d3-a456-426614174000", "status": "Closed"},
    ]
    changeorder.set_client(mock_client)
    changeorder.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["list_contracts"].fn(
        DB_TOKEN,
        PROJECT_ID,
        status="Open",
    )
    assert result["ok"] is True
    assert len(result["data"]["contracts"]) == 1
    assert result["data"]["contracts"][0]["status"] == "Open"
    mock_client.get_contracts.assert_awaited_once_with(
        DB_TOKEN,
        PROJECT_ID,
        search=None,
        status="Open",
        sort_by=None,
        sort_direction="asc",
    )


@pytest.mark.asyncio
async def test_get_project_health_packet_returns_contract_rollups() -> None:
    mcp = FastMCP("test-workflows-project")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_project.return_value = {"projectID": PROJECT_ID}
    mock_client.get_estimates.return_value = [{"estimateID": ESTIMATE_ID}]
    mock_client.get_contracts.return_value = [{"contractID": CONTRACT_ID, "status": "Open"}]
    mock_client.get_pcos.return_value = [{"pcoID": "1", "status": "Open"}]
    mock_client.get_contract_statuses.return_value = [{"status": "Open"}]
    workflows.set_client(mock_client)
    workflows.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["get_project_health_packet"].fn(DB_TOKEN, PROJECT_ID)
    assert result["ok"] is True
    assert result["data"]["summary"]["contract_count"] == 1
    assert result["data"]["summary"]["estimate_count"] == 1
    assert result["data"]["summary"]["status_totals"]["Open"] == 1


@pytest.mark.asyncio
async def test_get_estimate_readiness_packet_infers_bid_summary() -> None:
    mcp = FastMCP("test-workflows-estimate")
    HANDLER_REGISTRY.clear()
    mock_client = AsyncMock()
    mock_client.get_estimate.return_value = {
        "estimateID": ESTIMATE_ID,
        "bidSummaries": [{"bidSummaryID": BID_SUMMARY_ID}],
    }
    mock_client.get_bid_breakdown_views.return_value = [{"bidBreakdownViewId": VIEW_ID}]
    mock_client.get_final_price.return_value = {"total": 123}
    workflows.set_client(mock_client)
    workflows.register(mcp, HANDLER_REGISTRY)

    result = await HANDLER_REGISTRY["get_estimate_readiness_packet"].fn(DB_TOKEN, ESTIMATE_ID)
    assert result["ok"] is True
    assert result["data"]["summary"]["bid_summary_id"] == BID_SUMMARY_ID
    assert result["data"]["readiness"]["ready_for_closeout_analysis"] is True
