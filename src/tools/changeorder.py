"""Changeorder-domain tools for Accubid MCP."""

from fastmcp import FastMCP

from ..client import AccubidClient
from ..pagination import normalize_list, paginate_items
from ..querying import apply_equals_filter, apply_search, apply_sort
from ..tool_runtime import execute_tool
from ..validation import (
    validate_database_token,
    validate_optional_text,
    validate_required_text,
    validate_uuid_like,
)

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register changeorder tools."""

    @mcp.tool()
    async def list_contracts(
        database_token: str,
        project_id: str,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List contracts for a project."""
        return await execute_tool(
            "list_contracts",
            lambda: _list_contracts(
                database_token,
                project_id,
                search=search,
                status=status,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "project_id": project_id,
                "search": search,
                "status": status,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def list_pcos(
        database_token: str,
        contract_id: str,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List PCOs for a contract."""
        return await execute_tool(
            "list_pcos",
            lambda: _list_pcos(
                database_token,
                contract_id,
                search=search,
                status=status,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "contract_id": contract_id,
                "search": search,
                "status": status,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_pco(database_token: str, pco_id: str) -> dict:
        """Get one PCO by id."""
        return await execute_tool(
            "get_pco",
            lambda: _get_pco(database_token, pco_id),
            context={"database_token": database_token, "pco_id": pco_id},
        )

    @mcp.tool()
    async def get_contract_cost_distribution(
        database_token: str,
        contract_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get contract cost distribution rows."""
        return await execute_tool(
            "get_contract_cost_distribution",
            lambda: _get_contract_cost_distribution(
                database_token, contract_id, page_index=page_index, page_size=page_size
            ),
            context={
                "database_token": database_token,
                "contract_id": contract_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_contract_quote_labels(
        database_token: str,
        contract_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get quote labels for a contract."""
        return await execute_tool(
            "get_contract_quote_labels",
            lambda: _get_contract_quote_labels(
                database_token, contract_id, page_index=page_index, page_size=page_size
            ),
            context={
                "database_token": database_token,
                "contract_id": contract_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_contract_subcontract_labels(
        database_token: str,
        contract_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get subcontract labels for a contract."""
        return await execute_tool(
            "get_contract_subcontract_labels",
            lambda: _get_contract_subcontract_labels(
                database_token, contract_id, page_index=page_index, page_size=page_size
            ),
            context={
                "database_token": database_token,
                "contract_id": contract_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_contract_statuses(
        database_token: str,
        contract_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get contract statuses."""
        return await execute_tool(
            "get_contract_statuses",
            lambda: _get_contract_statuses(
                database_token, contract_id, page_index=page_index, page_size=page_size
            ),
            context={
                "database_token": database_token,
                "contract_id": contract_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def trigger_pco_extension_file(
        database_token: str,
        pco_id: str,
        connection_id: str,
    ) -> dict:
        """Trigger SignalR extension-file generation for a PCO."""
        return await execute_tool(
            "trigger_pco_extension_file",
            lambda: _trigger_pco_extension_file(database_token, pco_id, connection_id),
            context={"database_token": database_token, "pco_id": pco_id},
        )

    @mcp.tool()
    async def send_changeorder_notification_test(connection_id: str) -> dict:
        """Send a SignalR test notification for changeorder service."""
        return await execute_tool(
            "send_changeorder_notification_test",
            lambda: _send_changeorder_notification_test(connection_id),
            context={"connection_id": connection_id},
        )

    async def _list_contracts(
        database_token: str,
        project_id: str,
        *,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        normalized_search = validate_optional_text("search", search, max_length=128)
        normalized_status = validate_optional_text("status", status, max_length=64)
        normalized_sort_by = validate_optional_text("sort_by", sort_by, max_length=64)
        normalized_sort_direction = validate_optional_text("sort_direction", sort_direction, max_length=8) or "asc"
        data = await _client.get_contracts(
            db_token,
            normalized_project_id,
            search=normalized_search,
            status=normalized_status,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        items = normalize_list(data)
        items = apply_search(
            items,
            search=normalized_search,
            search_fields=("name", "contractName", "number", "contractNumber"),
        )
        items = apply_equals_filter(
            items,
            value=normalized_status,
            field_aliases=("status", "contractStatus", "contract_status"),
        )
        items = apply_sort(
            items,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
            sort_fields={
                "name": ("name", "contractName"),
                "number": ("number", "contractNumber"),
                "status": ("status", "contractStatus"),
            },
        )
        paged = paginate_items(items, page_index=page_index, page_size=page_size)
        return {"contracts": paged["items"], "pagination": paged["pagination"]}

    async def _list_pcos(
        database_token: str,
        contract_id: str,
        *,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        normalized_search = validate_optional_text("search", search, max_length=128)
        normalized_status = validate_optional_text("status", status, max_length=64)
        normalized_sort_by = validate_optional_text("sort_by", sort_by, max_length=64)
        normalized_sort_direction = validate_optional_text("sort_direction", sort_direction, max_length=8) or "asc"
        data = await _client.get_pcos(
            db_token,
            normalized_contract_id,
            search=normalized_search,
            status=normalized_status,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        items = normalize_list(data)
        items = apply_search(
            items,
            search=normalized_search,
            search_fields=("name", "pcoName", "number", "pcoNumber", "description"),
        )
        items = apply_equals_filter(
            items,
            value=normalized_status,
            field_aliases=("status", "pcoStatus", "pco_status"),
        )
        items = apply_sort(
            items,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
            sort_fields={
                "name": ("name", "pcoName"),
                "number": ("number", "pcoNumber"),
                "status": ("status", "pcoStatus"),
            },
        )
        paged = paginate_items(items, page_index=page_index, page_size=page_size)
        return {"pcos": paged["items"], "pagination": paged["pagination"]}

    async def _get_pco(database_token: str, pco_id: str) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_pco_id = validate_uuid_like("pco_id", pco_id)
        return {"pco": await _client.get_pco(db_token, normalized_pco_id)}

    async def _get_contract_cost_distribution(
        database_token: str,
        contract_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await _client.get_contract_cost_distribution(db_token, normalized_contract_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"items": paged["items"], "pagination": paged["pagination"]}

    async def _get_contract_quote_labels(
        database_token: str,
        contract_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await _client.get_contract_quote_labels(db_token, normalized_contract_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"labels": paged["items"], "pagination": paged["pagination"]}

    async def _get_contract_subcontract_labels(
        database_token: str,
        contract_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await _client.get_contract_subcontract_labels(db_token, normalized_contract_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"labels": paged["items"], "pagination": paged["pagination"]}

    async def _get_contract_statuses(
        database_token: str,
        contract_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await _client.get_contract_statuses(db_token, normalized_contract_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"statuses": paged["items"], "pagination": paged["pagination"]}

    async def _trigger_pco_extension_file(database_token: str, pco_id: str, connection_id: str) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_pco_id = validate_uuid_like("pco_id", pco_id)
        normalized_connection_id = validate_required_text("connection_id", connection_id, max_length=512)
        return {
            "result": await _client.trigger_pco_extension_file(
                db_token,
                normalized_pco_id,
                normalized_connection_id,
            )
        }

    async def _send_changeorder_notification_test(connection_id: str) -> dict:
        normalized_connection_id = validate_required_text("connection_id", connection_id, max_length=512)
        return {"result": await _client.send_changeorder_notification_test(normalized_connection_id)}

    if handler_registry is not None:
        handler_registry["list_contracts"] = list_contracts
        handler_registry["list_pcos"] = list_pcos
        handler_registry["get_pco"] = get_pco
        handler_registry["get_contract_cost_distribution"] = get_contract_cost_distribution
        handler_registry["get_contract_quote_labels"] = get_contract_quote_labels
        handler_registry["get_contract_subcontract_labels"] = get_contract_subcontract_labels
        handler_registry["get_contract_statuses"] = get_contract_statuses
        handler_registry["trigger_pco_extension_file"] = trigger_pco_extension_file
        handler_registry["send_changeorder_notification_test"] = send_changeorder_notification_test
