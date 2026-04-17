"""Tests for delegated (actor token) auth helpers."""

import pytest

from src.config import Config
from src.errors import AuthError


@pytest.mark.asyncio
async def test_resolve_outbound_server_mode_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "server")
    from src.delegated_jwt import resolve_outbound_access_token

    assert await resolve_outbound_access_token() is None


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_missing_bearer_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    import src.delegated_jwt as dj

    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: None)
    with pytest.raises(AuthError, match="delegated"):
        await dj.resolve_outbound_access_token()


@pytest.mark.asyncio
async def test_resolve_outbound_hybrid_no_bearer_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "hybrid")
    import src.delegated_jwt as dj

    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: None)
    assert await dj.resolve_outbound_access_token() is None


def test_missing_required_scopes_openid_implicit_via_iss_sub() -> None:
    from src.delegated_jwt import _missing_required_scopes

    payload = {
        "scope": "accubid_agentic_ai",
        "iss": "https://identity.trimble.com/",
        "sub": "user-123",
    }
    assert _missing_required_scopes(["accubid_agentic_ai", "openid"], payload) == []


def test_missing_required_scopes_openid_not_implicit_without_oidc_claims() -> None:
    from src.delegated_jwt import _missing_required_scopes

    payload = {"scope": "accubid_agentic_ai"}
    assert _missing_required_scopes(["openid"], payload) == ["openid"]


def test_missing_required_scopes_openid_explicit_in_scope() -> None:
    from src.delegated_jwt import _missing_required_scopes

    payload = {"scope": "accubid_agentic_ai openid"}
    assert _missing_required_scopes(["openid"], payload) == []
