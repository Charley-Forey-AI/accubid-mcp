"""Opinionated multi-step workflow tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..client import AccubidClient
from ..concurrency import run_bounded
from ..pagination import normalize_list
from ..querying import first_present
from ..tool_runtime import execute_tool
from ..validation import normalize_yyyymmdd, validate_optional_text, validate_uuid_like

_client: AccubidClient | None = None


def set_client(client: AccubidClient) -> None:
    global _client
    _client = client


def register(mcp: FastMCP, handler_registry: dict | None = None) -> None:
    """Register workflow-oriented tools."""

    @mcp.tool()
    async def get_project_health_packet(
        database_token: str,
        project_id: str,
        due_date_start: str | None = None,
        due_date_end: str | None = None,
        include_contract_statuses: bool = True,
    ) -> dict:
        """Return a one-call health packet for project execution and pipeline visibility."""
        return await execute_tool(
            "get_project_health_packet",
            lambda: _get_project_health_packet(
                database_token,
                project_id,
                due_date_start=due_date_start,
                due_date_end=due_date_end,
                include_contract_statuses=include_contract_statuses,
            ),
            context={
                "database_token": database_token,
                "project_id": project_id,
                "due_date_start": due_date_start,
                "due_date_end": due_date_end,
            },
        )

    @mcp.tool()
    async def get_estimate_readiness_packet(
        database_token: str,
        estimate_id: str,
        bid_summary_id: str | None = None,
        include_first_breakdown_page: bool = False,
    ) -> dict:
        """Return estimate readiness details for downstream closeout/changeorder workflows."""
        return await execute_tool(
            "get_estimate_readiness_packet",
            lambda: _get_estimate_readiness_packet(
                database_token,
                estimate_id,
                bid_summary_id=bid_summary_id,
                include_first_breakdown_page=include_first_breakdown_page,
            ),
            context={
                "database_token": database_token,
                "estimate_id": estimate_id,
                "bid_summary_id": bid_summary_id,
                "include_first_breakdown_page": include_first_breakdown_page,
            },
        )

    async def _get_project_health_packet(
        database_token: str,
        project_id: str,
        *,
        due_date_start: str | None = None,
        due_date_end: str | None = None,
        include_contract_statuses: bool = True,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        normalized_due_start = validate_optional_text("due_date_start", due_date_start, max_length=16)
        normalized_due_end = validate_optional_text("due_date_end", due_date_end, max_length=16)
        if normalized_due_start and not normalized_due_end:
            normalized_due_end = normalized_due_start
        if normalized_due_end and not normalized_due_start:
            normalized_due_start = normalized_due_end
        if normalized_due_start and normalized_due_end:
            normalized_due_start = normalize_yyyymmdd("due_date_start", normalized_due_start)
            normalized_due_end = normalize_yyyymmdd("due_date_end", normalized_due_end)

        project, estimates, contracts = await run_bounded(
            [
                _client.get_project(db_token, normalized_project_id),
                _client.get_estimates(db_token, normalized_project_id),
                _client.get_contracts(db_token, normalized_project_id),
            ]
        )

        contract_items = normalize_list(contracts)
        status_totals: dict[str, int] = {}
        contract_status_packets: list[dict[str, Any]] = []

        if include_contract_statuses:
            async def _load_contract(contract: dict[str, Any]) -> dict[str, Any]:
                contract_id = first_present(contract, ("contractID", "contractId", "contract_id"))
                if not isinstance(contract_id, str) or not contract_id.strip():
                    return {"contract": contract, "contract_id": None, "status_counts": {}, "pco_count": 0}
                normalized_contract_id = validate_uuid_like("contract_id", contract_id)
                pcos, statuses = await run_bounded(
                    [
                        _client.get_pcos(db_token, normalized_contract_id),
                        _client.get_contract_statuses(db_token, normalized_contract_id),
                    ]
                )
                pco_items = normalize_list(pcos)
                status_rows = normalize_list(statuses)
                status_counts: dict[str, int] = {
                    str(first_present(row, ("status", "name", "value")) or "unknown"): 0
                    for row in status_rows
                    if isinstance(row, dict)
                }
                for pco in pco_items:
                    if not isinstance(pco, dict):
                        continue
                    key = str(first_present(pco, ("status", "pcoStatus", "pco_status")) or "unknown")
                    status_counts[key] = status_counts.get(key, 0) + 1
                return {
                    "contract": contract,
                    "contract_id": normalized_contract_id,
                    "status_counts": status_counts,
                    "pco_count": len(pco_items),
                }

            contract_status_packets = await run_bounded(
                [_load_contract(contract) for contract in contract_items if isinstance(contract, dict)]
            )
            for packet in contract_status_packets:
                for key, count in packet.get("status_counts", {}).items():
                    status_totals[key] = status_totals.get(key, 0) + int(count)

        due_date_estimates = []
        if normalized_due_start and normalized_due_end:
            due_date_estimates = normalize_list(
                await _client.get_estimates_by_due_date(db_token, normalized_due_start, normalized_due_end)
            )

        return {
            "contract": {"schema": "accubid.workflow.project_health_packet.v1"},
            "summary": {
                "database_token": db_token,
                "project_id": normalized_project_id,
                "estimate_count": len(normalize_list(estimates)),
                "contract_count": len(contract_items),
                "status_totals": status_totals,
                "due_window_estimate_count": len(due_date_estimates),
            },
            "project": project,
            "estimates": normalize_list(estimates),
            "contracts": contract_items,
            "contract_status_packets": contract_status_packets,
            "due_window_estimates": due_date_estimates,
        }

    async def _get_estimate_readiness_packet(
        database_token: str,
        estimate_id: str,
        *,
        bid_summary_id: str | None = None,
        include_first_breakdown_page: bool = False,
    ) -> dict:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        estimate, views = await run_bounded(
            [
                _client.get_estimate(db_token, normalized_estimate_id),
                _client.get_bid_breakdown_views(db_token, normalized_estimate_id),
            ]
        )
        estimate_dict = estimate if isinstance(estimate, dict) else {}
        normalized_bid_summary_value = validate_optional_text("bid_summary_id", bid_summary_id)
        normalized_bid_summary_id = (
            validate_uuid_like("bid_summary_id", normalized_bid_summary_value)
            if normalized_bid_summary_value is not None
            else None
        )
        if normalized_bid_summary_id is None:
            bid_summaries = normalize_list(
                first_present(estimate_dict, ("bidSummaries", "BidSummaries", "bid_summaries")) or []
            )
            first_bid_summary = bid_summaries[0] if bid_summaries else {}
            inferred_id = first_present(
                first_bid_summary if isinstance(first_bid_summary, dict) else {},
                ("bidSummaryID", "bidSummaryId", "bid_summary_id"),
            )
            if isinstance(inferred_id, str) and inferred_id.strip():
                normalized_bid_summary_id = validate_uuid_like("bid_summary_id", inferred_id)

        final_price = None
        if normalized_bid_summary_id:
            final_price = await _client.get_final_price(db_token, normalized_bid_summary_id)

        breakdown_preview = None
        view_items = normalize_list(views)
        if include_first_breakdown_page and normalized_bid_summary_id and view_items:
            first_view = view_items[0] if isinstance(view_items[0], dict) else {}
            view_id = first_present(first_view, ("bidBreakdownViewId", "bid_breakdown_view_id"))
            if isinstance(view_id, str) and view_id.strip():
                breakdown_preview = await _client.get_bid_breakdown(
                    db_token,
                    normalized_bid_summary_id,
                    validate_uuid_like("bid_breakdown_view_id", view_id),
                    page_index=0,
                )

        return {
            "contract": {"schema": "accubid.workflow.estimate_readiness_packet.v1"},
            "summary": {
                "database_token": db_token,
                "estimate_id": normalized_estimate_id,
                "bid_summary_id": normalized_bid_summary_id,
                "view_count": len(view_items),
                "has_final_price": final_price is not None,
            },
            "estimate": estimate,
            "bid_breakdown_views": view_items,
            "final_price": final_price,
            "bid_breakdown_preview": breakdown_preview,
            "readiness": {
                "has_bid_summary_id": normalized_bid_summary_id is not None,
                "has_bid_breakdown_views": bool(view_items),
                "ready_for_closeout_analysis": normalized_bid_summary_id is not None and bool(view_items),
            },
        }

    if handler_registry is not None:
        handler_registry["get_project_health_packet"] = get_project_health_packet
        handler_registry["get_estimate_readiness_packet"] = get_estimate_readiness_packet
