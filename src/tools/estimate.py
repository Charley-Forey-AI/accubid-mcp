"""Estimate-domain tools for Accubid MCP."""

from typing import Optional

from fastmcp import FastMCP

from ..client import AccubidClient
from ..pagination import normalize_list, paginate_items
from ..querying import apply_search, apply_sort
from ..tool_runtime import execute_tool
from ..validation import (
    normalize_yyyymmdd,
    validate_optional_text,
    validate_required_text,
    validate_uuid_like,
)

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register estimate tools."""

    @mcp.tool()
    async def list_estimates(
        database_token: str,
        project_id: str,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List estimates for a project."""
        return await execute_tool(
            "list_estimates",
            lambda: _list_estimates(
                database_token,
                project_id,
                search=search,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "project_id": project_id,
                "search": search,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_estimate(database_token: str, estimate_id: str) -> dict:
        """Get one estimate by id."""
        return await execute_tool(
            "get_estimate",
            lambda: _get_estimate(database_token, estimate_id),
            context={"database_token": database_token, "estimate_id": estimate_id},
        )

    @mcp.tool()
    async def create_estimate(
        database_token: str,
        project_id: str,
        name: str,
        number: str,
        industry: str,
        copy_date_from_project: bool = True,
    ) -> dict:
        """Create a new estimate."""
        return await execute_tool(
            "create_estimate",
            lambda: _create_estimate(
                database_token,
                project_id,
                name,
                number,
                industry,
                copy_date_from_project,
            ),
            context={"database_token": database_token, "project_id": project_id},
        )

    @mcp.tool()
    async def get_estimates_by_due_date(
        database_token: str,
        start_date: str,
        end_date: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get estimates with due dates between two yyyymmdd values."""
        return await execute_tool(
            "get_estimates_by_due_date",
            lambda: _get_estimates_by_due_date(
                database_token,
                start_date,
                end_date,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "start_date": start_date,
                "end_date": end_date,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def trigger_estimate_extension_file(
        database_token: str,
        estimate_id: str,
        connection_id: str,
        bid_summary_id: Optional[str] = None,
    ) -> dict:
        """Trigger SignalR extension-file generation for an estimate.

        This endpoint requires a valid SignalR `connection_id`.
        """
        return await execute_tool(
            "trigger_estimate_extension_file",
            lambda: _trigger_estimate_extension_file(
                database_token,
                estimate_id,
                connection_id,
                bid_summary_id=bid_summary_id,
            ),
            context={"database_token": database_token, "estimate_id": estimate_id},
        )

    @mcp.tool()
    async def send_estimate_notification_test(connection_id: str) -> dict:
        """Send a SignalR notification test for estimate service."""
        return await execute_tool(
            "send_estimate_notification_test",
            lambda: _send_estimate_notification_test(connection_id),
            context={"connection_id": connection_id},
        )

    async def _list_estimates(
        database_token: str,
        project_id: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        normalized_search = validate_optional_text("search", search, max_length=128)
        normalized_sort_by = validate_optional_text("sort_by", sort_by, max_length=64)
        normalized_sort_direction = validate_optional_text("sort_direction", sort_direction, max_length=8) or "asc"
        data = await _client.get_estimates(
            db_token,
            normalized_project_id,
            search=normalized_search,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        items = normalize_list(data)
        items = apply_search(
            items,
            search=normalized_search,
            search_fields=("name", "estimateName", "number", "estimateNumber"),
        )
        items = apply_sort(
            items,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
            sort_fields={
                "name": ("name", "estimateName"),
                "number": ("number", "estimateNumber"),
                "due_date": ("dueDate", "due_date"),
            },
        )
        paged = paginate_items(items, page_index=page_index, page_size=page_size)
        return {"estimates": paged["items"], "pagination": paged["pagination"]}

    async def _get_estimate(database_token: str, estimate_id: str) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        return {"estimate": await _client.get_estimate(db_token, normalized_estimate_id)}

    async def _create_estimate(
        database_token: str,
        project_id: str,
        name: str,
        number: str,
        industry: str,
        copy_date_from_project: bool = True,
    ) -> dict:
        payload = {
            "databaseToken": validate_uuid_like("database_token", database_token),
            "projectID": validate_uuid_like("project_id", project_id),
            "name": validate_required_text("name", name),
            "number": validate_required_text("number", number),
            "industry": validate_required_text("industry", industry),
            "copyDateFromProject": copy_date_from_project,
        }
        return {"result": await _client.create_estimate(payload)}

    async def _get_estimates_by_due_date(
        database_token: str,
        start_date: str,
        end_date: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_start_date = normalize_yyyymmdd("start_date", start_date)
        normalized_end_date = normalize_yyyymmdd("end_date", end_date)
        data = await _client.get_estimates_by_due_date(db_token, normalized_start_date, normalized_end_date)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"estimates": paged["items"], "pagination": paged["pagination"]}

    async def _trigger_estimate_extension_file(
        database_token: str,
        estimate_id: str,
        connection_id: str,
        bid_summary_id: Optional[str] = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        normalized_connection_id = validate_required_text("connection_id", connection_id, max_length=512)
        normalized_bid_summary_value = validate_optional_text("bid_summary_id", bid_summary_id)
        normalized_bid_summary_id = (
            validate_uuid_like("bid_summary_id", normalized_bid_summary_value)
            if normalized_bid_summary_value is not None
            else None
        )
        result = await _client.trigger_estimate_extension_file(
            db_token,
            normalized_estimate_id,
            normalized_connection_id,
            bid_summary_id=normalized_bid_summary_id,
        )
        return {"result": result}

    async def _send_estimate_notification_test(connection_id: str) -> dict:
        normalized_connection_id = validate_required_text("connection_id", connection_id, max_length=512)
        return {"result": await _client.send_estimate_notification_test(normalized_connection_id)}

    if handler_registry is not None:
        handler_registry["list_estimates"] = list_estimates
        handler_registry["get_estimate"] = get_estimate
        handler_registry["create_estimate"] = create_estimate
        handler_registry["get_estimates_by_due_date"] = get_estimates_by_due_date
        handler_registry["trigger_estimate_extension_file"] = trigger_estimate_extension_file
        handler_registry["send_estimate_notification_test"] = send_estimate_notification_test
