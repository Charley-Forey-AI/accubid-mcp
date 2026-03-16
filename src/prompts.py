"""MCP prompts for common Accubid workflows."""

from __future__ import annotations

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register reusable workflow prompts for MCP clients."""

    @mcp.prompt(name="bid_discovery")
    async def bid_discovery(database_token: str = "") -> str:
        db_hint = (
            f"Use database_token `{database_token}` if available."
            if database_token
            else "Start with list_databases to discover database tokens."
        )
        return (
            "Goal: discover active bids from Accubid.\n"
            "Steps:\n"
            "1) Call list_databases.\n"
            f"2) {db_hint}\n"
            "3) Call list_projects(database_token=...).\n"
            "4) Pick a project and call list_estimates(database_token=..., project_id=...).\n"
            "5) Return a concise summary of estimate name, number, and IDs."
        )

    @mcp.prompt(name="closeout_for_estimate")
    async def closeout_for_estimate(
        database_token: str,
        estimate_id: str,
        bid_summary_id: str = "",
    ) -> str:
        bid_step = (
            f"Use bid_summary_id `{bid_summary_id}` for get_final_price and get_bid_breakdown."
            if bid_summary_id
            else "If bid_summary_id is missing, call get_estimate first and choose one from bid summaries."
        )
        return (
            "Goal: run closeout analysis for one estimate.\n"
            "Steps:\n"
            f"1) Call get_estimate(database_token='{database_token}', estimate_id='{estimate_id}').\n"
            f"2) {bid_step}\n"
            f"3) Call get_bid_breakdown_views(database_token='{database_token}', estimate_id='{estimate_id}').\n"
            "4) Call get_final_price(database_token=..., bid_summary_id=...).\n"
            "5) Optionally call get_bid_breakdown(database_token=..., "
            "bid_summary_id=..., bid_breakdown_view_id=..., page_index=0).\n"
            "6) Summarize final price, key breakdown views, and top risks."
        )

    @mcp.prompt(name="changeorder_flow")
    async def changeorder_flow(database_token: str, project_id: str, contract_id: str = "") -> str:
        contract_step = (
            f"Use contract_id `{contract_id}` for downstream calls."
            if contract_id
            else "Call list_contracts first and select a contract_id."
        )
        return (
            "Goal: inspect change orders for a project.\n"
            "Steps:\n"
            f"1) Call list_contracts(database_token='{database_token}', project_id='{project_id}').\n"
            f"2) {contract_step}\n"
            "3) Call list_pcos(database_token=..., contract_id=...).\n"
            "4) For one PCO, call get_pco(database_token=..., pco_id=...).\n"
            "5) Optionally call get_contract_statuses(database_token=..., contract_id=...).\n"
            "6) Return a summary of open/closed PCOs and notable items."
        )

    @mcp.prompt(name="pipeline_report")
    async def pipeline_report(database_token: str, start_date: str, end_date: str = "") -> str:
        date_hint = (
            f"Use end_date `{end_date}`."
            if end_date
            else "If end_date is omitted, use start_date as both start and end."
        )
        return (
            "Goal: produce a pipeline report for bid activity.\n"
            "Steps:\n"
            "1) If database_token is missing, call list_databases and choose one token.\n"
            f"2) {date_hint}\n"
            f"3) Call get_pipeline_summary(database_token='{database_token}', "
            f"start_date='{start_date}', end_date='{end_date or start_date}').\n"
            "4) Summarize project count, estimate count in date window, and top items needing follow-up."
        )

    @mcp.prompt(name="full_closeout_report")
    async def full_closeout_report(
        database_token: str,
        estimate_id: str,
        bid_summary_id: str = "",
    ) -> str:
        bid_step = (
            f"Use bid_summary_id `{bid_summary_id}`."
            if bid_summary_id
            else "If bid_summary_id is missing, let get_closeout_summary derive the first available bid summary."
        )
        return (
            "Goal: produce a full closeout report for one estimate.\n"
            "Steps:\n"
            f"1) {bid_step}\n"
            f"2) Call get_closeout_summary(database_token='{database_token}', estimate_id='{estimate_id}', "
            "bid_summary_id='...', include_first_breakdown_page=true).\n"
            "3) If deeper detail is needed, call get_bid_breakdown for additional pages/views.\n"
            "4) Summarize final price, key view context, and closeout risks."
        )

    @mcp.prompt(name="changeorder_summary_by_project")
    async def changeorder_summary_by_project(
        database_token: str,
        project_id: str,
        contract_id: str = "",
    ) -> str:
        contract_hint = (
            f"Focus on contract_id `{contract_id}`."
            if contract_id
            else "If contract_id is omitted, summarize all contracts for the project."
        )
        return (
            "Goal: summarize changeorder activity for a project.\n"
            "Steps:\n"
            f"1) {contract_hint}\n"
            f"2) Call get_changeorder_summary(database_token='{database_token}', project_id='{project_id}', "
            "contract_id='...').\n"
            "3) Return open/closed status totals, top contracts by PCO volume, and notable exceptions."
        )
