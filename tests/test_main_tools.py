import pytest

from src.config import Config
from src.main import list_available_tools


@pytest.mark.asyncio
async def test_list_available_tools_domain_filter() -> None:
    result = await list_available_tools.fn(domain="database")
    assert result["ok"] is True
    tools = result["data"]["tools"]
    assert tools
    assert all(tool.get("domain") == "database" for tool in tools)
    assert "runtime" in tools[0]


@pytest.mark.asyncio
async def test_list_available_tools_unknown_domain() -> None:
    result = await list_available_tools.fn(domain="unknown-domain")
    assert result["ok"] is True
    assert result["data"]["tools"] == []


@pytest.mark.asyncio
async def test_list_available_tools_applies_namespace_aliases() -> None:
    original_namespace = Config.ACCUBID_TOOL_NAMESPACE
    try:
        Config.ACCUBID_TOOL_NAMESPACE = "accubid"
        result = await list_available_tools.fn(domain="database")
        assert result["ok"] is True
        assert all(tool["name"].startswith("accubid/") for tool in result["data"]["tools"])
    finally:
        Config.ACCUBID_TOOL_NAMESPACE = original_namespace
