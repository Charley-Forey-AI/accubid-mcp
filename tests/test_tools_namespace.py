from unittest.mock import AsyncMock

from fastmcp import FastMCP

from src.config import Config
from src.registry import HANDLER_REGISTRY
from src.tools import register_tools


def test_register_tools_adds_namespaced_aliases() -> None:
    original_namespace = Config.ACCUBID_TOOL_NAMESPACE
    original_disable_flags = (
        Config.ACCUBID_TOOLS_DISABLE_DATABASE,
        Config.ACCUBID_TOOLS_DISABLE_PROJECT,
        Config.ACCUBID_TOOLS_DISABLE_ESTIMATE,
        Config.ACCUBID_TOOLS_DISABLE_CLOSEOUT,
        Config.ACCUBID_TOOLS_DISABLE_CHANGEORDER,
    )
    try:
        Config.ACCUBID_TOOL_NAMESPACE = "accubid"
        Config.ACCUBID_TOOLS_DISABLE_DATABASE = False
        Config.ACCUBID_TOOLS_DISABLE_PROJECT = True
        Config.ACCUBID_TOOLS_DISABLE_ESTIMATE = True
        Config.ACCUBID_TOOLS_DISABLE_CLOSEOUT = True
        Config.ACCUBID_TOOLS_DISABLE_CHANGEORDER = True
        HANDLER_REGISTRY.clear()

        register_tools(FastMCP("test-namespace"), AsyncMock())

        assert "list_databases" in HANDLER_REGISTRY
        assert "accubid/list_databases" in HANDLER_REGISTRY
    finally:
        Config.ACCUBID_TOOL_NAMESPACE = original_namespace
        (
            Config.ACCUBID_TOOLS_DISABLE_DATABASE,
            Config.ACCUBID_TOOLS_DISABLE_PROJECT,
            Config.ACCUBID_TOOLS_DISABLE_ESTIMATE,
            Config.ACCUBID_TOOLS_DISABLE_CLOSEOUT,
            Config.ACCUBID_TOOLS_DISABLE_CHANGEORDER,
        ) = original_disable_flags
