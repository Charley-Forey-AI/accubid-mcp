"""Tool registration for Accubid MCP."""

from fastmcp import FastMCP

from ..config import Config
from ..registry import HANDLER_REGISTRY
from . import changeorder, closeout, context, database, estimate, insights, project, workflows


def register_tools(mcp_instance: FastMCP, client) -> None:
    """Register all tool modules."""
    if not Config.ACCUBID_TOOLS_DISABLE_DATABASE:
        database.set_client(client)
        database.register(mcp_instance, HANDLER_REGISTRY)
    if not Config.ACCUBID_TOOLS_DISABLE_PROJECT:
        project.set_client(client)
        project.register(mcp_instance, HANDLER_REGISTRY)
    if not Config.ACCUBID_TOOLS_DISABLE_ESTIMATE:
        estimate.set_client(client)
        estimate.register(mcp_instance, HANDLER_REGISTRY)
    if not Config.ACCUBID_TOOLS_DISABLE_CLOSEOUT:
        closeout.set_client(client)
        closeout.register(mcp_instance, HANDLER_REGISTRY)
    if not Config.ACCUBID_TOOLS_DISABLE_CHANGEORDER:
        changeorder.set_client(client)
        changeorder.register(mcp_instance, HANDLER_REGISTRY)
    insights.set_client(client)
    insights.register(mcp_instance, HANDLER_REGISTRY)
    context.set_client(client)
    context.register(mcp_instance, HANDLER_REGISTRY)
    workflows.set_client(client)
    workflows.register(mcp_instance, HANDLER_REGISTRY)
    _register_tool_namespace_aliases(mcp_instance)


def _register_tool_namespace_aliases(mcp_instance: FastMCP) -> None:
    """Optionally register `namespace/tool_name` aliases for all tools."""
    namespace = Config.ACCUBID_TOOL_NAMESPACE
    if not namespace:
        return

    # Iterate over a stable snapshot so we can extend HANDLER_REGISTRY safely.
    for tool_name, tool_obj in list(HANDLER_REGISTRY.items()):
        if "/" in tool_name:
            continue
        alias_name = f"{namespace}/{tool_name}"
        if alias_name in HANDLER_REGISTRY:
            continue
        aliased_tool = mcp_instance.tool(name=alias_name)(tool_obj.fn)
        HANDLER_REGISTRY[alias_name] = aliased_tool
