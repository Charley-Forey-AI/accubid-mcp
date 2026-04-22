"""Closeout-domain tools for Accubid MCP."""


from fastmcp import FastMCP

from ..client import AccubidClient
from ..pagination import normalize_list, paginate_items
from ..tool_runtime import execute_tool
from ..validation import (
    validate_database_token,
    validate_optional_int_from_any,
    validate_uuid_like,
)

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register closeout tools."""

    @mcp.tool()
    async def get_final_price(database_token: str, bid_summary_id: str) -> dict:
        """Get final price data for a bid summary."""
        return await execute_tool(
            "get_final_price",
            lambda: _get_final_price(database_token, bid_summary_id),
            context={"database_token": database_token, "bid_summary_id": bid_summary_id},
        )

    @mcp.tool()
    async def get_bid_breakdown_views(
        database_token: str,
        estimate_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List bid breakdown views for an estimate."""
        return await execute_tool(
            "get_bid_breakdown_views",
            lambda: _get_bid_breakdown_views(
                database_token,
                estimate_id,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "estimate_id": estimate_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_bid_breakdown(
        database_token: str,
        bid_summary_id: str,
        bid_breakdown_view_id: str,
        page_index: int | str | None = None,
    ) -> dict:
        """Get paginated bid breakdown rows."""
        return await execute_tool(
            "get_bid_breakdown",
            lambda: _get_bid_breakdown(
                database_token,
                bid_summary_id,
                bid_breakdown_view_id,
                page_index=page_index,
            ),
            context={
                "database_token": database_token,
                "bid_summary_id": bid_summary_id,
                "bid_breakdown_view_id": bid_breakdown_view_id,
                "page_index": page_index,
            },
        )

    async def _get_final_price(database_token: str, bid_summary_id: str) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_bid_summary_id = validate_uuid_like("bid_summary_id", bid_summary_id)
        return {"final_price": await _client.get_final_price(db_token, normalized_bid_summary_id)}

    async def _get_bid_breakdown_views(
        database_token: str,
        estimate_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        data = await _client.get_bid_breakdown_views(db_token, normalized_estimate_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"views": paged["items"], "pagination": paged["pagination"]}

    async def _get_bid_breakdown(
        database_token: str,
        bid_summary_id: str,
        bid_breakdown_view_id: str,
        page_index: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_bid_summary_id = validate_uuid_like("bid_summary_id", bid_summary_id)
        normalized_view_id = validate_uuid_like("bid_breakdown_view_id", bid_breakdown_view_id)
        normalized_page_index = validate_optional_int_from_any("page_index", page_index, min_value=0)
        data = await _client.get_bid_breakdown(
            db_token,
            normalized_bid_summary_id,
            normalized_view_id,
            page_index=normalized_page_index,
        )
        return _normalize_bid_breakdown_result(data)

    def _normalize_bid_breakdown_result(data: object) -> dict:
        if not isinstance(data, dict):
            return {
                "items": normalize_list(data),
                "pagination": {
                    "page_index": 0,
                    "page_size": len(normalize_list(data)),
                    "total_count": len(normalize_list(data)),
                    "total_pages": 1 if normalize_list(data) else 0,
                    "has_next_page": False,
                },
            }

        page_index_raw = data.get("pageIndex", data.get("page_index", 0))
        page_size_raw = data.get("pageSize", data.get("page_size"))
        total_items_raw = data.get("totalItems", data.get("total_count"))
        items = normalize_list(data.get("items", []))

        normalized_page_index = validate_optional_int_from_any(
            "page_index",
            page_index_raw,
            min_value=0,
        ) or 0
        normalized_page_size = validate_optional_int_from_any(
            "page_size",
            page_size_raw if page_size_raw is not None else len(items),
            min_value=1,
        ) or max(1, len(items))
        normalized_total_count = validate_optional_int_from_any(
            "total_items",
            total_items_raw if total_items_raw is not None else len(items),
            min_value=0,
        ) or 0
        total_pages = (
            (normalized_total_count + normalized_page_size - 1) // normalized_page_size
            if normalized_total_count > 0
            else 0
        )
        has_next_page = (normalized_page_index + 1) * normalized_page_size < normalized_total_count

        return {
            "items": items,
            "pagination": {
                "page_index": normalized_page_index,
                "page_size": normalized_page_size,
                "total_count": normalized_total_count,
                "total_pages": total_pages,
                "has_next_page": has_next_page,
            },
            "links": data.get("links"),
        }

    if handler_registry is not None:
        handler_registry["get_final_price"] = get_final_price
        handler_registry["get_bid_breakdown_views"] = get_bid_breakdown_views
        handler_registry["get_bid_breakdown"] = get_bid_breakdown
