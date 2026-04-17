"""Tests for Accubid API error detail enrichment (900909 diagnostics)."""

from src.client import _build_accubid_api_error_details
from src.request_context import reset_request_token_claims, set_request_token_claims


def test_build_details_includes_hint_for_900909() -> None:
    body = '{"fault":{"code":"900909","message":"Authentication Failure"}}'
    reset = set_request_token_claims(
        {"azp": "app-guid", "sub": "user-guid", "scopes": ["accubid_agentic_ai"]}
    )
    try:
        d = _build_accubid_api_error_details(
            method="GET",
            endpoint_path="/databases",
            url="https://cloud.api.trimble.com/anywhere/database/v1/databases",
            safe_body=body,
            full_text_len=len(body),
            status_code=401,
        )
        assert d["actor_azp"] == "app-guid"
        assert d["actor_sub"] == "user-guid"
        assert d["actor_scopes"] == ["accubid_agentic_ai"]
        assert "900909" in d["hint"]
        assert "app-guid" in d["hint"]
    finally:
        reset_request_token_claims(reset)
