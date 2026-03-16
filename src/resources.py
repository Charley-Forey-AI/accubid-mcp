"""MCP resources for common read-only Accubid data."""

from __future__ import annotations

import json

from fastmcp import FastMCP

from .client import AccubidClient
from .pagination import normalize_list
from .querying import first_present
from .validation import normalize_yyyymmdd, validate_uuid_like


def _json_payload(data: object) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def register_resources(mcp: FastMCP, client: AccubidClient) -> None:
    """Register read-only resources for common workflows."""

    @mcp.resource("accubid://databases", name="accubid_databases", mime_type="application/json")
    async def databases_resource() -> str:
        data = await client.get_databases()
        payload = {"databases": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/folders",
        name="accubid_folders",
        mime_type="application/json",
    )
    async def folders_resource(database_token: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        data = await client.get_folders(db_token)
        payload = {"folders": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/folders/{parent_folder_id}",
        name="accubid_child_folders",
        mime_type="application/json",
    )
    async def child_folders_resource(database_token: str, parent_folder_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        folder_id = validate_uuid_like("parent_folder_id", parent_folder_id)
        data = await client.get_folders(db_token, folder_id)
        payload = {"folders": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/projects",
        name="accubid_projects",
        mime_type="application/json",
    )
    async def projects_resource(database_token: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        data = await client.get_projects(db_token)
        payload = {"projects": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/projects/{project_id}",
        name="accubid_project",
        mime_type="application/json",
    )
    async def project_resource(database_token: str, project_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        payload = {"project": await client.get_project(db_token, normalized_project_id)}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/projects/{project_id}/estimates",
        name="accubid_estimates",
        mime_type="application/json",
    )
    async def estimates_resource(database_token: str, project_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        data = await client.get_estimates(db_token, normalized_project_id)
        payload = {"estimates": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/estimates/{estimate_id}",
        name="accubid_estimate",
        mime_type="application/json",
    )
    async def estimate_resource(database_token: str, estimate_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        payload = {"estimate": await client.get_estimate(db_token, normalized_estimate_id)}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/projects/{project_id}/contracts",
        name="accubid_contracts",
        mime_type="application/json",
    )
    async def contracts_resource(database_token: str, project_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        data = await client.get_contracts(db_token, normalized_project_id)
        payload = {"contracts": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/contracts/{contract_id}/pcos",
        name="accubid_pcos",
        mime_type="application/json",
    )
    async def pcos_resource(database_token: str, contract_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await client.get_pcos(db_token, normalized_contract_id)
        payload = {"pcos": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/contracts/{contract_id}/statuses",
        name="accubid_contract_statuses",
        mime_type="application/json",
    )
    async def contract_statuses_resource(database_token: str, contract_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_contract_id = validate_uuid_like("contract_id", contract_id)
        data = await client.get_contract_statuses(db_token, normalized_contract_id)
        payload = {"statuses": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/estimates/{estimate_id}/bid-breakdown-views",
        name="accubid_bid_breakdown_views",
        mime_type="application/json",
    )
    async def bid_breakdown_views_resource(database_token: str, estimate_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_estimate_id = validate_uuid_like("estimate_id", estimate_id)
        data = await client.get_bid_breakdown_views(db_token, normalized_estimate_id)
        payload = {"views": data if isinstance(data, list) else [data]}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://databases/{database_token}/bid-summaries/{bid_summary_id}/final-price",
        name="accubid_final_price",
        mime_type="application/json",
    )
    async def final_price_resource(database_token: str, bid_summary_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_bid_summary_id = validate_uuid_like("bid_summary_id", bid_summary_id)
        payload = {"final_price": await client.get_final_price(db_token, normalized_bid_summary_id)}
        return _json_payload(payload)

    @mcp.resource(
        "accubid://context/project/{database_token}/{project_id}",
        name="accubid_project_context",
        mime_type="application/json",
    )
    async def project_context_resource(database_token: str, project_id: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_project_id = validate_uuid_like("project_id", project_id)
        project = await client.get_project(db_token, normalized_project_id)
        estimates = normalize_list(await client.get_estimates(db_token, normalized_project_id))
        contracts = normalize_list(await client.get_contracts(db_token, normalized_project_id))
        payload = {
            "summary": {
                "project_id": normalized_project_id,
                "estimate_count": len(estimates),
                "contract_count": len(contracts),
            },
            "project": project,
            "estimates": estimates,
            "contracts": contracts,
        }
        return _json_payload(payload)

    @mcp.resource(
        "accubid://insights/pipeline/{database_token}/{start_date}/{end_date}",
        name="accubid_pipeline_summary",
        mime_type="application/json",
    )
    async def pipeline_summary_resource(database_token: str, start_date: str, end_date: str) -> str:
        db_token = validate_uuid_like("database_token", database_token)
        normalized_start_date = normalize_yyyymmdd("start_date", start_date)
        normalized_end_date = normalize_yyyymmdd("end_date", end_date)
        rollups = normalize_list(await client.get_project_estimate_bid_summaries(db_token))
        estimates = normalize_list(
            await client.get_estimates_by_due_date(db_token, normalized_start_date, normalized_end_date)
        )
        project_ids = {
            first_present(item, ("projectID", "projectId", "project_id"))
            for item in rollups
            if isinstance(item, dict)
        }
        project_ids.discard(None)
        payload = {
            "summary": {
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
                "total_rollups": len(rollups),
                "total_estimates_in_window": len(estimates),
                "unique_project_count": len(project_ids),
            },
            "rollups": rollups,
            "estimates": estimates,
        }
        return _json_payload(payload)
