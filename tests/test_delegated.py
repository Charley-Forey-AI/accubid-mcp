"""Tests for delegated (actor token) auth helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Config
from src.errors import AuthError


@pytest.fixture(autouse=True)
def _reset_obo_cache() -> None:
    import src.delegated_jwt as dj

    dj._obo_cache.clear()
    dj._token_endpoint_cache = None
    yield
    dj._obo_cache.clear()
    dj._token_endpoint_cache = None


@pytest.mark.asyncio
async def test_resolve_outbound_server_mode_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "server")
    from src.delegated_jwt import resolve_outbound_access_token

    assert await resolve_outbound_access_token() == (None, None)


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
    assert await dj.resolve_outbound_access_token() == (None, None)


@pytest.mark.asyncio
async def test_resolve_outbound_hybrid_skip_obo_uses_server_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH", "true")
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "hybrid")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "openid accubid_agentic_ai anywhere-database")
    import src.delegated_jwt as dj

    async def fake_verify(_t: str) -> dict:
        return {"sub": "user-1", "azp": "studio-app"}

    monkeypatch.setattr(dj, "verify_delegated_jwt", fake_verify)
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "actor.raw.jwt")

    async def boom(*_a: object, **_kw: object) -> dict:  # pragma: no cover - must not run
        raise AssertionError("token exchange must be skipped")

    monkeypatch.setattr(dj, "exchange_on_behalf_of", boom)

    token, claims = await dj.resolve_outbound_access_token()
    assert token is None
    assert claims["sub"] == "user-1"
    assert claims["azp"] == "studio-app"


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_does_not_honor_hybrid_only_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH applies only to hybrid mode."""
    monkeypatch.setenv("ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH", "true")
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "openid accubid_agentic_ai")
    import src.delegated_jwt as dj

    async def fake_verify(_t: str) -> dict:
        return {"sub": "user-1", "azp": "studio"}

    monkeypatch.setattr(dj, "verify_delegated_jwt", fake_verify)
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "actor.raw.jwt")

    calls: list[dict] = []

    async def fake_exchange(session, **kw):  # noqa: ARG001
        calls.append(kw)
        return {"access_token": "exchanged", "expires_in": 3600}

    monkeypatch.setattr(dj, "exchange_on_behalf_of", fake_exchange)
    monkeypatch.setattr(
        dj,
        "resolve_token_endpoint",
        AsyncMock(return_value="https://id.trimble.com/oauth/token"),
    )

    token, claims = await dj.resolve_outbound_access_token()
    assert token == "exchanged"
    assert claims["sub"] == "user-1"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_exchanges_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "openid accubid_agentic_ai")
    import src.delegated_jwt as dj

    async def fake_verify(_t: str) -> dict:
        return {"sub": "user-1", "azp": "studio-app"}

    monkeypatch.setattr(dj, "verify_delegated_jwt", fake_verify)
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "actor.raw.jwt")

    calls: list[dict] = []

    async def fake_exchange(session, **kw):  # noqa: ARG001
        calls.append(kw)
        return {"access_token": "exchanged-at", "expires_in": 3600}

    monkeypatch.setattr(dj, "exchange_on_behalf_of", fake_exchange)
    monkeypatch.setattr(
        dj,
        "resolve_token_endpoint",
        AsyncMock(return_value="https://id.trimble.com/oauth/token"),
    )

    token, claims = await dj.resolve_outbound_access_token()
    assert token == "exchanged-at"
    assert claims["sub"] == "user-1"
    assert claims["azp"] == "studio-app"
    assert len(calls) == 1
    assert calls[0]["subject_token"] == "actor.raw.jwt"
    assert calls[0]["scope"] == "openid accubid_agentic_ai"
    assert calls[0].get("resource") is None


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_passes_token_exchange_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCUBID_TOKEN_EXCHANGE_RESOURCE", "https://cloud.api.trimble.com/anywhere")
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "openid accubid_agentic_ai")
    import src.delegated_jwt as dj

    async def fake_verify(_t: str) -> dict:
        return {"sub": "user-1", "azp": "studio-app"}

    monkeypatch.setattr(dj, "verify_delegated_jwt", fake_verify)
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "actor.raw.jwt")

    calls: list[dict] = []

    async def fake_exchange(session, **kw):  # noqa: ARG001
        calls.append(kw)
        return {"access_token": "exchanged-at", "expires_in": 3600}

    monkeypatch.setattr(dj, "exchange_on_behalf_of", fake_exchange)
    monkeypatch.setattr(
        dj,
        "resolve_token_endpoint",
        AsyncMock(return_value="https://id.trimble.com/oauth/token"),
    )

    await dj.resolve_outbound_access_token()
    assert len(calls) == 1
    assert calls[0]["resource"] == "https://cloud.api.trimble.com/anywhere"


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_obo_cache_reuses_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "accubid_agentic_ai")
    import src.delegated_jwt as dj

    async def fake_verify(_t: str) -> dict:
        return {"sub": "same-user", "azp": "studio"}

    monkeypatch.setattr(dj, "verify_delegated_jwt", fake_verify)
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "bearer.one")

    n = {"calls": 0}

    async def fake_exchange(session, **kw):  # noqa: ARG001
        n["calls"] += 1
        return {"access_token": "tok-v1", "expires_in": 3600}

    monkeypatch.setattr(dj, "exchange_on_behalf_of", fake_exchange)
    monkeypatch.setattr(
        dj,
        "resolve_token_endpoint",
        AsyncMock(return_value="https://id.trimble.com/oauth/token"),
    )

    t1, _ = await dj.resolve_outbound_access_token()
    t2, _ = await dj.resolve_outbound_access_token()
    assert t1 == t2 == "tok-v1"
    assert n["calls"] == 1


@pytest.mark.asyncio
async def test_resolve_outbound_delegated_exchange_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "ACCUBID_AUTH_MODE", "delegated")
    monkeypatch.setattr(Config, "CLIENT_ID", "cid")
    monkeypatch.setattr(Config, "CLIENT_SECRET", "sec")
    monkeypatch.setattr(Config, "ACCUBID_SCOPE", "openid")
    import src.delegated_jwt as dj

    monkeypatch.setattr(
        dj,
        "verify_delegated_jwt",
        AsyncMock(return_value={"sub": "u", "azp": "z"}),
    )
    monkeypatch.setattr(dj, "extract_bearer_raw_from_request", lambda: "raw")

    async def boom(session, **kw):  # noqa: ARG001
        raise AuthError("OBO failed", details={"status": 400})

    monkeypatch.setattr(dj, "exchange_on_behalf_of", boom)
    monkeypatch.setattr(
        dj,
        "resolve_token_endpoint",
        AsyncMock(return_value="https://id.trimble.com/oauth/token"),
    )

    with pytest.raises(AuthError, match="OBO failed"):
        await dj.resolve_outbound_access_token()


@pytest.mark.asyncio
async def test_exchange_on_behalf_of_success_mock_session() -> None:
    from src.oauth_flow import exchange_on_behalf_of

    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value='{"access_token":"at1","expires_in":1800}')
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=response)
    post_cm.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(return_value=post_cm)

    out = await exchange_on_behalf_of(
        session,
        token_endpoint="https://id.trimble.com/oauth/token",
        client_id="c",
        client_secret="s",
        subject_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig",
        scope="openid accubid_agentic_ai",
    )
    assert out["access_token"] == "at1"
    session.post.assert_called_once()
    _url, kwargs = session.post.call_args
    assert kwargs["data"].startswith("grant_type=")
    assert "token-exchange" in kwargs["data"]
    assert "subject_token=" in kwargs["data"]
    import base64

    assert kwargs["headers"]["Authorization"] == "Basic " + base64.b64encode(b"c:s").decode()


@pytest.mark.asyncio
async def test_exchange_on_behalf_of_includes_resource_in_form() -> None:
    from src.oauth_flow import exchange_on_behalf_of

    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value='{"access_token":"at1"}')
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=response)
    post_cm.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(return_value=post_cm)

    await exchange_on_behalf_of(
        session,
        token_endpoint="https://id.trimble.com/oauth/token",
        client_id="c",
        client_secret="s",
        subject_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig",
        scope="openid accubid_agentic_ai",
        resource="https://cloud.api.trimble.com/anywhere",
    )
    _url, kwargs = session.post.call_args
    assert "resource=" in kwargs["data"]
    assert "cloud.api.trimble.com" in kwargs["data"]


@pytest.mark.asyncio
async def test_exchange_on_behalf_of_retries_jwt_after_not_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.oauth_flow as of
    from src.oauth_flow import exchange_on_behalf_of

    seq = iter([False, True])

    def fake_looks(_t: str) -> bool:
        return next(seq)

    monkeypatch.setattr(of, "looks_like_jwt", fake_looks)

    r400 = MagicMock()
    r400.status = 400
    r400.text = AsyncMock(return_value="not supported for this token type")
    cm400 = MagicMock()
    cm400.__aenter__ = AsyncMock(return_value=r400)
    cm400.__aexit__ = AsyncMock(return_value=None)

    r200 = MagicMock()
    r200.status = 200
    r200.text = AsyncMock(return_value='{"access_token":"after-retry","expires_in":120}')
    cm200 = MagicMock()
    cm200.__aenter__ = AsyncMock(return_value=r200)
    cm200.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(side_effect=[cm400, cm200])

    out = await exchange_on_behalf_of(
        session,
        token_endpoint="https://id.trimble.com/oauth/token",
        client_id="c",
        client_secret="s",
        subject_token="opaque-or-edge",
        scope="s",
    )
    assert out["access_token"] == "after-retry"
    assert session.post.call_count == 2


@pytest.mark.asyncio
async def test_exchange_on_behalf_of_non_200_raises() -> None:
    from src.oauth_flow import exchange_on_behalf_of

    response = MagicMock()
    response.status = 403
    response.text = AsyncMock(return_value="forbidden")
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=response)
    post_cm.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.post = MagicMock(return_value=post_cm)

    with pytest.raises(AuthError, match="403"):
        await exchange_on_behalf_of(
            session,
            token_endpoint="https://id.trimble.com/oauth/token",
            client_id="c",
            client_secret="s",
            subject_token="a.b.c",
            scope="s",
        )


def test_safe_claims_from_payload_extracts_actor_fields() -> None:
    from src.delegated_jwt import safe_claims_from_payload

    payload = {
        "azp": "client-uuid",
        "sub": "user-uuid",
        "account_id": "acct-1",
        "data_region": "us",
        "iss": "https://id.trimble.com",
        "exp": 9999999999,
        "scope": "accubid_agentic_ai openid",
    }
    claims = safe_claims_from_payload(payload)
    assert claims["azp"] == "client-uuid"
    assert claims["sub"] == "user-uuid"
    assert claims["account_id"] == "acct-1"
    assert claims["data_region"] == "us"
    assert claims["scopes"] == ["accubid_agentic_ai", "openid"]


def test_safe_claims_prepends_openid_when_omitted_from_scope_claim() -> None:
    """Studio may show openid but JWT scope string only lists accubid_agentic_ai."""
    from src.delegated_jwt import safe_claims_from_payload

    payload = {
        "azp": "app-id",
        "sub": "user-id",
        "iss": "https://id.trimble.com",
        "scope": "accubid_agentic_ai",
    }
    claims = safe_claims_from_payload(payload)
    assert claims["scopes"] == ["openid", "accubid_agentic_ai"]


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
