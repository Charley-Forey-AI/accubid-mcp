"""Project-domain tools for Accubid MCP."""

from typing import Optional

from fastmcp import FastMCP

from ..client import AccubidClient
from ..pagination import normalize_list, paginate_items
from ..querying import apply_search, apply_sort
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
    """Register project tools."""

    @mcp.tool()
    async def list_folders(
        database_token: str,
        parent_folder_id: Optional[str] = None,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List folders for a database token.

        Use without `parent_folder_id` for root folders, or pass `parent_folder_id`
        to list children.
        """
        return await execute_tool(
            "list_folders",
            lambda: _list_folders(
                database_token, parent_folder_id, page_index=page_index, page_size=page_size
            ),
            context={
                "database_token": database_token,
                "parent_folder_id": parent_folder_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def create_folder(
        database_token: str, description: str, parent_folder_id: Optional[str] = None
    ) -> dict:
        """Create a folder in Accubid project service."""
        return await execute_tool(
            "create_folder",
            lambda: _create_folder(database_token, description, parent_folder_id),
            context={"database_token": database_token, "parent_folder_id": parent_folder_id},
        )

    @mcp.tool()
    async def list_projects(
        database_token: str,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """List projects for a database token."""
        return await execute_tool(
            "list_projects",
            lambda: _list_projects(
                database_token,
                search=search,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "search": search,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_project(database_token: str, project_id: str) -> dict:
        """Get one project by id."""
        return await execute_tool(
            "get_project",
            lambda: _get_project(database_token, project_id),
            context={"database_token": database_token, "project_id": project_id},
        )

    @mcp.tool()
    async def create_project(database_token: str, folder_id: str, name: str, number: str) -> dict:
        """Create a project."""
        return await execute_tool(
            "create_project",
            lambda: _create_project(database_token, folder_id, name, number),
            context={"database_token": database_token, "folder_id": folder_id},
        )

    @mcp.tool()
    async def get_last_projects(
        database_token: str,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get recently-used projects for a database."""
        return await execute_tool(
            "get_last_projects",
            lambda: _get_last_projects(
                database_token,
                search=search,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "search": search,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_project_estimate_bid_summaries(
        database_token: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get project/estimate/bid-summary rollup list for a database."""
        return await execute_tool(
            "get_project_estimate_bid_summaries",
            lambda: _get_project_estimate_bid_summaries(
                database_token, page_index=page_index, page_size=page_size
            ),
            context={"database_token": database_token, "page_index": page_index, "page_size": page_size},
        )

    async def _list_folders(
        database_token: str,
        parent_folder_id: Optional[str] = None,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_parent_id = validate_optional_text("parent_folder_id", parent_folder_id)
        parent_id = (
            validate_uuid_like("parent_folder_id", normalized_parent_id)
            if normalized_parent_id is not None
            else None
        )
        data = await _client.get_folders(db_token, parent_id)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"folders": paged["items"], "pagination": paged["pagination"]}

    async def _create_folder(
        database_token: str,
        description: str,
        parent_folder_id: Optional[str] = None,
    ) -> dict:
        normalized_parent_id = validate_optional_text("parent_folder_id", parent_folder_id)
        payload = {
            "databaseToken": validate_database_token("database_token", database_token),
            "description": validate_required_text("description", description),
            "parentFolderID": (
                validate_uuid_like("parent_folder_id", normalized_parent_id)
                if normalized_parent_id is not None
                else None
            ),
        }
        return {"result": await _client.create_folder(payload)}

    async def _list_projects(
        database_token: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_search = validate_optional_text("search", search, max_length=128)
        normalized_sort_by = validate_optional_text("sort_by", sort_by, max_length=64)
        normalized_sort_direction = validate_optional_text("sort_direction", sort_direction, max_length=8) or "asc"
        data = await _client.get_projects(
            db_token,
            search=normalized_search,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        items = normalize_list(data)
        items = apply_search(
            items,
            search=normalized_search,
            search_fields=("name", "projectName", "number", "projectNumber"),
        )
        items = apply_sort(
            items,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
            sort_fields={
                "name": ("name", "projectName"),
                "number": ("number", "projectNumber"),
                "created": ("createdOn", "created_at"),
            },
        )
        paged = paginate_items(items, page_index=page_index, page_size=page_size)
        return {"projects": paged["items"], "pagination": paged["pagination"]}

    async def _get_project(database_token: str, project_id: str) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        return {"project": await _client.get_project(db_token, normalized_project_id)}

    async def _create_project(database_token: str, folder_id: str, name: str, number: str) -> dict:
        payload = {
            "databaseToken": validate_database_token("database_token", database_token),
            "folderID": validate_uuid_like("folder_id", folder_id),
            "name": validate_required_text("name", name),
            "number": validate_required_text("number", number),
        }
        return {"result": await _client.create_project(payload)}

    async def _get_last_projects(
        database_token: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = "asc",
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        normalized_search = validate_optional_text("search", search, max_length=128)
        normalized_sort_by = validate_optional_text("sort_by", sort_by, max_length=64)
        normalized_sort_direction = validate_optional_text("sort_direction", sort_direction, max_length=8) or "asc"
        data = await _client.get_last_projects(
            db_token,
            search=normalized_search,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        items = normalize_list(data)
        items = apply_search(
            items,
            search=normalized_search,
            search_fields=("name", "projectName", "number", "projectNumber"),
        )
        items = apply_sort(
            items,
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
            sort_fields={
                "name": ("name", "projectName"),
                "number": ("number", "projectNumber"),
                "last_used": ("lastUsedOn", "last_used_on"),
            },
        )
        paged = paginate_items(items, page_index=page_index, page_size=page_size)
        return {"projects": paged["items"], "pagination": paged["pagination"]}

    async def _get_project_estimate_bid_summaries(
        database_token: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_database_token("database_token", database_token)
        data = await _client.get_project_estimate_bid_summaries(db_token)
        paged = paginate_items(normalize_list(data), page_index=page_index, page_size=page_size)
        return {"items": paged["items"], "pagination": paged["pagination"]}

    if handler_registry is not None:
        handler_registry["list_folders"] = list_folders
        handler_registry["create_folder"] = create_folder
        handler_registry["list_projects"] = list_projects
        handler_registry["get_project"] = get_project
        handler_registry["create_project"] = create_project
        handler_registry["get_last_projects"] = get_last_projects
        handler_registry["get_project_estimate_bid_summaries"] = get_project_estimate_bid_summaries
