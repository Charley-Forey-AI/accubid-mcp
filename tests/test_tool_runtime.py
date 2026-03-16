import pytest

from src.config import Config
from src.tool_runtime import execute_tool


@pytest.mark.asyncio
async def test_execute_tool_success() -> None:
    async def op() -> dict:
        return {"value": 1}

    result = await execute_tool("test_success", op)
    assert result["ok"] is True
    assert result["data"] == {"value": 1}


@pytest.mark.asyncio
async def test_execute_tool_failure() -> None:
    async def op() -> dict:
        raise RuntimeError("boom")

    result = await execute_tool("test_fail", op)
    assert result["ok"] is False
    assert result["error"]["code"] == "internal_error"
    assert result["error"]["message"] == "boom"


@pytest.mark.asyncio
async def test_execute_tool_applies_snake_case_when_enabled() -> None:
    original = Config.ACCUBID_RESPONSE_SNAKE_CASE
    Config.ACCUBID_RESPONSE_SNAKE_CASE = True
    try:
        async def op() -> dict:
            return {"projectID": "P1", "bidBreakdownViews": [{"viewID": "V1"}]}

        result = await execute_tool("test_snake_case", op)
        assert result["ok"] is True
        assert result["data"] == {"project_id": "P1", "bid_breakdown_views": [{"view_id": "V1"}]}
    finally:
        Config.ACCUBID_RESPONSE_SNAKE_CASE = original
