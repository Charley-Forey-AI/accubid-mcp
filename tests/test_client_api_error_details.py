"""Tests for Accubid API error detail enrichment (900909 diagnostics)."""

import base64
import json

import pytest

from src.client import _build_accubid_api_error_details


def _minimal_jwt(payload: dict) -> str:
    hdr = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{hdr}.{body}.signature"


def test_build_details_includes_hint_for_900909(monkeypatch: pytest.MonkeyPatch) -> None:
    body = '{"fault":{"code":"900909","message":"Authentication Failure"}}'
    outbound = _minimal_jwt({"azp": "outbound-subscribed-app"})
    actor = _minimal_jwt(
        {"azp": "app-guid", "sub": "user-guid", "scope": "openid accubid_agentic_ai"}
    )
    monkeypatch.setattr("src.client.get_request_outbound_token", lambda: outbound)
    monkeypatch.setattr("src.client.get_actor_token", lambda: actor)

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
    assert d["actor_scopes"] == "openid accubid_agentic_ai"
    assert d["outbound_azp"] == "outbound-subscribed-app"
    assert d["outbound_token_shape"] == "jwt"
    assert "900909" not in d["hint"] or "Trimble 900909" in d["hint"]
    assert "outbound-subscribed-app" in d["hint"]
    assert "actor_azp=app-guid" in d["hint"]


def test_build_details_opaque_outbound_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _minimal_jwt({"azp": "studio-app"})
    monkeypatch.setattr("src.client.get_request_outbound_token", lambda: "opaque-token")
    monkeypatch.setattr("src.client.get_actor_token", lambda: actor)

    d = _build_accubid_api_error_details(
        method="GET",
        endpoint_path="/databases",
        url="https://x",
        safe_body='{"fault":{"code":"900909"}}',
        full_text_len=99,
        status_code=401,
    )
    assert d["outbound_token_shape"] == "opaque_or_malformed"
    assert "opaque" in d["hint"].lower() or "decodable" in d["hint"].lower()
