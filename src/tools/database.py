"""Database tools for Accubid MCP."""

from fastmcp import FastMCP

from ..client import AccubidClient
from ..pagination import normalize_list, paginate_items
from ..tool_runtime import execute_tool

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register database tools."""

    @mcp.tool()
    async def list_databases(
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List databases available to the authenticated user.

        Call this first in most workflows to get the `databaseToken` needed by
        project, estimate, closeout, and changeorder tools.
        """
        return await execute_tool(
            "list_databases",
            lambda: _list_databases(page_index=page_index, page_size=page_size),
            context={"page_index": page_index, "page_size": page_size},
        )

    async def _list_databases(
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        data = await _client.get_databases()
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"databases": paged["items"], "pagination": paged["pagination"]}

    if handler_registry is not None:
        handler_registry["list_databases"] = list_databases
