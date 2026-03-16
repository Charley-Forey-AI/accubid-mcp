"""Context-aggregator tools to reduce multi-step data gathering."""

from __future__ import annotations

from fastmcp import FastMCP

from ..client import AccubidClient
from ..concurrency import run_bounded
from ..pagination import normalize_list, paginate_items
from ..querying import first_present
from ..tool_runtime import execute_tool
from ..validation import validate_optional_text, validate_uuid_like

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register context aggregator tools."""

    @mcp.tool()
    async def get_project_context(
        database_token: str,
        project_id: str,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Fetch project, estimates, and contracts in one call."""
        return await execute_tool(
            "get_project_context",
            lambda: _get_project_context(
                database_token,
                project_id,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "project_id": project_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    @mcp.tool()
    async def get_estimate_context(
        database_token: str,
        estimate_id: str,
        bid_summary_id: str | None = None,
        include_first_breakdown_page: bool = False,
    ) -> dict:
        """Fetch estimate metadata with closeout context in one call."""
        return await execute_tool(
            "get_estimate_context",
            lambda: _get_estimate_context(
                database_token,
                estimate_id,
                bid_summary_id=bid_summary_id,
                include_first_breakdown_page=include_first_breakdown_page,
            ),
            context={
                "database_token": database_token,
                "estimate_id": estimate_id,
                "bid_summary_id": bid_summary_id,
            },
        )

    async def _get_project_context(
        database_token: str,
        project_id: str,
        *,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        project, estimates_raw, contracts_raw = await run_bounded(
            [
                _client.get_project(db_token, normalized_project_id),
                _client.get_estimates(db_token, normalized_project_id),
                _client.get_contracts(db_token, normalized_project_id),
            ]
        )
        estimates = normalize_list(estimates_raw)
        contracts = normalize_list(contracts_raw)
        paged_estimates = paginate_items(estimates, page_index=page_index, page_size=page_size)
        paged_contracts = paginate_items(contracts, page_index=page_index, page_size=page_size)

        return {
            "contract": {"schema": "accubid.context.project_context.v1"},
            "summary": {
                "database_token": db_token,
                "project_id": normalized_project_id,
                "estimate_count": len(estimates),
                "contract_count": len(contracts),
            },
            "project": project,
            "estimates": paged_estimates["items"],
            "estimates_pagination": paged_estimates["pagination"],
            "contracts": paged_contracts["items"],
            "contracts_pagination": paged_contracts["pagination"],
        }

    async def _get_estimate_context(
        database_token: str,
        estimate_id: str,
        *,
        bid_summary_id: str | None = None,
        include_first_breakdown_page: bool = False,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        estimate, views_raw = await run_bounded(
            [
                _client.get_estimate(db_token, normalized_estimate_id),
                _client.get_bid_breakdown_views(db_token, normalized_estimate_id),
            ]
        )
        views = normalize_list(views_raw)

        normalized_bid_summary_id = validate_optional_text("bid_summary_id", bid_summary_id)
        selected_bid_summary_id = (
            validate_uuid_like("bid_summary_id", normalized_bid_summary_id)
            if normalized_bid_summary_id is not None
            else None
        )
        if selected_bid_summary_id is None and isinstance(estimate, dict):
            bid_summaries = normalize_list(
                first_present(estimate, ("bidSummaries", "BidSummaries", "bid_summaries")) or []
            )
            first_bid_summary = bid_summaries[0] if bid_summaries else None
            if isinstance(first_bid_summary, dict):
                first_id = first_present(first_bid_summary, ("bidSummaryID", "bidSummaryId", "bid_summary_id"))
                if isinstance(first_id, str) and first_id.strip():
                    selected_bid_summary_id = validate_uuid_like("bid_summary_id", first_id)

        final_price = (
            await _client.get_final_price(db_token, selected_bid_summary_id)
            if selected_bid_summary_id is not None
            else None
        )
        breakdown_preview = None
        if include_first_breakdown_page and selected_bid_summary_id and views:
            first_view = views[0]
            if isinstance(first_view, dict):
                view_id = first_present(first_view, ("bidBreakdownViewId", "bid_breakdown_view_id"))
                if isinstance(view_id, str) and view_id.strip():
                    breakdown_preview = await _client.get_bid_breakdown(
                        db_token,
                        selected_bid_summary_id,
                        validate_uuid_like("bid_breakdown_view_id", view_id),
                        page_index=0,
                    )

        return {
            "contract": {"schema": "accubid.context.estimate_context.v1"},
            "summary": {
                "database_token": db_token,
                "estimate_id": normalized_estimate_id,
                "bid_summary_id": selected_bid_summary_id,
                "view_count": len(views),
            },
            "estimate": estimate,
            "bid_breakdown_views": views,
            "final_price": final_price,
            "bid_breakdown_preview": breakdown_preview,
        }

    if handler_registry is not None:
        handler_registry["get_project_context"] = get_project_context
        handler_registry["get_estimate_context"] = get_estimate_context

