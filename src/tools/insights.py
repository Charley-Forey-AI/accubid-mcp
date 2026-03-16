"""Insights and analytics tools composed from existing Accubid APIs."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..client import AccubidClient
from ..concurrency import run_bounded
from ..pagination import normalize_list, paginate_items
from ..querying import first_present
from ..tool_runtime import execute_tool
from ..validation import normalize_yyyymmdd, validate_optional_text, validate_uuid_like

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def _to_status_key(value: Any) -> str:
    if value is None:
        return "unknown"
    normalized = str(value).strip()
    return normalized or "unknown"


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register composable insights tools."""

    @mcp.tool()
    async def get_pipeline_summary(
        database_token: str,
        start_date: str,
        end_date: str | None = None,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Get a pipeline-oriented rollup for estimates and due dates."""
        return await execute_tool(
            "get_pipeline_summary",
            lambda: _get_pipeline_summary(
                database_token,
                start_date,
                end_date=end_date,
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
    async def get_closeout_summary(
        database_token: str,
        estimate_id: str,
        bid_summary_id: str | None = None,
        include_first_breakdown_page: bool = False,
    ) -> dict:
        """Get a high-level closeout summary for one estimate."""
        return await execute_tool(
            "get_closeout_summary",
            lambda: _get_closeout_summary(
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

    @mcp.tool()
    async def get_changeorder_summary(
        database_token: str,
        project_id: str,
        contract_id: str | None = None,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        """Summarize change orders by contract and status for a project."""
        return await execute_tool(
            "get_changeorder_summary",
            lambda: _get_changeorder_summary(
                database_token,
                project_id,
                contract_id=contract_id,
                page_index=page_index,
                page_size=page_size,
            ),
            context={
                "database_token": database_token,
                "project_id": project_id,
                "contract_id": contract_id,
                "page_index": page_index,
                "page_size": page_size,
            },
        )

    async def _get_pipeline_summary(
        database_token: str,
        start_date: str,
        *,
        end_date: str | None = None,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_start_date = normalize_yyyymmdd("start_date", start_date)
        normalized_end_date = normalize_yyyymmdd("end_date", end_date or normalized_start_date)

        rollups_raw, estimates_raw = await run_bounded(
            [
                _client.get_project_estimate_bid_summaries(db_token),
                _client.get_estimates_by_due_date(
                    db_token,
                    normalized_start_date,
                    normalized_end_date,
                ),
            ]
        )
        rollups = normalize_list(rollups_raw)
        estimates = normalize_list(estimates_raw)
        paged_rollups = paginate_items(rollups, page_index=page_index, page_size=page_size)
        paged_estimates = paginate_items(estimates, page_index=page_index, page_size=page_size)
        unique_project_ids = {
            first_present(item, ("projectID", "projectId", "project_id"))
            for item in rollups
            if isinstance(item, dict)
        }
        unique_project_ids.discard(None)

        return {
            "contract": {"schema": "accubid.insights.pipeline_summary.v1"},
            "summary": {
                "database_token": db_token,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
                "total_rollups": len(rollups),
                "total_estimates_in_window": len(estimates),
                "unique_project_count": len(unique_project_ids),
            },
            "rollups": paged_rollups["items"],
            "rollups_pagination": paged_rollups["pagination"],
            "estimates": paged_estimates["items"],
            "estimates_pagination": paged_estimates["pagination"],
        }

    async def _get_closeout_summary(
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
            "contract": {"schema": "accubid.insights.closeout_summary.v1"},
            "summary": {
                "database_token": db_token,
                "estimate_id": normalized_estimate_id,
                "bid_summary_id": selected_bid_summary_id,
                "view_count": len(views),
            },
            "estimate": estimate,
            "final_price": final_price,
            "bid_breakdown_views": views,
            "bid_breakdown_preview": breakdown_preview,
        }

    async def _get_changeorder_summary(
        database_token: str,
        project_id: str,
        *,
        contract_id: str | None = None,
        page_index: int | str | None = None,
        page_size: int | str | None = None,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        normalized_contract_id = validate_optional_text("contract_id", contract_id)
        selected_contract_id = (
            validate_uuid_like("contract_id", normalized_contract_id)
            if normalized_contract_id is not None
            else None
        )

        all_contracts = normalize_list(await _client.get_contracts(db_token, normalized_project_id))
        contracts_to_summarize = [
            contract
            for contract in all_contracts
            if selected_contract_id is None
            or (
                isinstance(contract, dict)
                and first_present(contract, ("contractID", "contractId", "contract_id")) == selected_contract_id
            )
        ]
        paged_contracts = paginate_items(
            contracts_to_summarize,
            page_index=page_index,
            page_size=page_size,
        )

        async def _summarize_contract(contract: Any) -> dict[str, Any] | None:
            if not isinstance(contract, dict):
                return None
            contract_token = first_present(contract, ("contractID", "contractId", "contract_id"))
            if not isinstance(contract_token, str) or not contract_token.strip():
                return None
            normalized_contract_id = validate_uuid_like("contract_id", contract_token)
            pcos_raw, statuses_raw = await run_bounded(
                [
                    _client.get_pcos(db_token, normalized_contract_id),
                    _client.get_contract_statuses(db_token, normalized_contract_id),
                ]
            )
            pcos = normalize_list(pcos_raw)
            statuses = normalize_list(statuses_raw)
            known_status_values = {
                _to_status_key(first_present(status, ("status", "name", "value")))
                for status in statuses
                if isinstance(status, dict)
            }
            per_contract_counts: dict[str, int] = {status: 0 for status in known_status_values if status}
            for pco in pcos:
                if not isinstance(pco, dict):
                    continue
                status_key = _to_status_key(first_present(pco, ("status", "pcoStatus", "pco_status")))
                per_contract_counts[status_key] = per_contract_counts.get(status_key, 0) + 1
            return {
                "contract_id": normalized_contract_id,
                "pco_count": len(pcos),
                "status_counts": per_contract_counts,
                "contract": contract,
            }

        maybe_summaries = await run_bounded([_summarize_contract(contract) for contract in paged_contracts["items"]])
        contract_summaries = [summary for summary in maybe_summaries if summary is not None]
        total_pco_count = sum(summary["pco_count"] for summary in contract_summaries)
        status_totals: dict[str, int] = {}
        for summary in contract_summaries:
            for status_key, count in summary["status_counts"].items():
                status_totals[status_key] = status_totals.get(status_key, 0) + int(count)

        return {
            "contract": {"schema": "accubid.insights.changeorder_summary.v1"},
            "summary": {
                "database_token": db_token,
                "project_id": normalized_project_id,
                "contract_count": len(contract_summaries),
                "total_pco_count": total_pco_count,
                "status_totals": status_totals,
            },
            "contracts": contract_summaries,
            "pagination": paged_contracts["pagination"],
        }

    if handler_registry is not None:
        handler_registry["get_pipeline_summary"] = get_pipeline_summary
        handler_registry["get_closeout_summary"] = get_closeout_summary
        handler_registry["get_changeorder_summary"] = get_changeorder_summary

