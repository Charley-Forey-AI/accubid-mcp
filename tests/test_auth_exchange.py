"""Tests for AccubidAuth on-behalf-of token exchange."""

import pytest

from src.auth import AccubidAuth
from src.errors import AuthError


def _minimal_jwt_three_parts() -> str:
    """Three segments so _looks_like_jwt is true."""
    return "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.ZpD8k"


@pytest.mark.asyncio
async def test_get_access_token_raises_without_actor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.auth.ensure_request_context_populated_from_http", lambda: None)
    monkeypatch.setattr("src.auth.get_actor_token", lambda: None)
    auth = AccubidAuth()
    with pytest.raises(AuthError, match="No Authorization: Bearer"):
        await auth.get_access_token()


@pytest.mark.asyncio
async def test_get_access_token_uses_cached_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    async def fake_exchange(self: AccubidAuth, actor: str, scope_str: str) -> tuple[str, float]:
        calls.append(1)
        return "exchanged-access-token", 3600.0

    monkeypatch.setattr(AccubidAuth, "_exchange", fake_exchange)
    monkeypatch.setattr("src.auth.ensure_request_context_populated_from_http", lambda: None)
    monkeypatch.setattr("src.auth.get_actor_token", lambda: _minimal_jwt_three_parts())

    auth = AccubidAuth()
    t1 = await auth.get_access_token()
    t2 = await auth.get_access_token()
    assert t1 == "exchanged-access-token"
    assert t2 == "exchanged-access-token"
    assert len(calls) == 1
