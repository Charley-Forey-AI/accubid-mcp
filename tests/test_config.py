import pytest

from src.config import Config


def test_accubid_scopes_splits_space_and_comma() -> None:
    original = Config.ACCUBID_SCOPE
    try:
        Config.ACCUBID_SCOPE = "anywhere-database, anywhere-project  anywhere-estimate"
        assert Config.accubid_scopes() == ["anywhere-database", "anywhere-project", "anywhere-estimate"]
    finally:
        Config.ACCUBID_SCOPE = original


def test_validate_raises_when_required_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original = (Config.CLIENT_ID, Config.CLIENT_SECRET, Config.ACCUBID_SCOPE)
    Config.CLIENT_ID = ""
    Config.CLIENT_SECRET = ""
    Config.ACCUBID_SCOPE = ""
    try:
        with pytest.raises(ValueError, match="Missing required env vars"):
            Config.validate()
    finally:
        Config.CLIENT_ID, Config.CLIENT_SECRET, Config.ACCUBID_SCOPE = original
        Config.validate()


def test_validate_rejects_insecure_prod_base_url() -> None:
    original = (Config.ENV, Config.ACCUBID_API_BASE_URL)
    Config.ENV = "production"
    Config.ACCUBID_API_BASE_URL = "http://example.com"
    try:
        with pytest.raises(ValueError, match="must use https://"):
            Config.validate()
    finally:
        Config.ENV, Config.ACCUBID_API_BASE_URL = original
        Config.validate()


def test_validate_delegated_requires_client_for_token_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delegated mode must have CLIENT_ID/SECRET/ACCUBID_SCOPE for Trimble OBO exchange."""
    original = (
        Config.ACCUBID_AUTH_MODE,
        Config.CLIENT_ID,
        Config.CLIENT_SECRET,
        Config.ACCUBID_SCOPE,
    )
    Config.ACCUBID_AUTH_MODE = "delegated"
    Config.CLIENT_ID = ""
    Config.CLIENT_SECRET = ""
    Config.ACCUBID_SCOPE = "openid accubid_agentic_ai"
    try:
        with pytest.raises(ValueError, match="token exchange"):
            Config.validate()
    finally:
        (
            Config.ACCUBID_AUTH_MODE,
            Config.CLIENT_ID,
            Config.CLIENT_SECRET,
            Config.ACCUBID_SCOPE,
        ) = original
        Config.validate()


def test_validate_rejects_invalid_auth_mode() -> None:
    original = Config.ACCUBID_AUTH_MODE
    Config.ACCUBID_AUTH_MODE = "invalid"
    try:
        with pytest.raises(ValueError, match="ACCUBID_AUTH_MODE"):
            Config.validate()
    finally:
        Config.ACCUBID_AUTH_MODE = original
        Config.validate()


def test_validate_rejects_invalid_oauth_grant() -> None:
    original = Config.ACCUBID_OAUTH_GRANT
    Config.ACCUBID_OAUTH_GRANT = "implicit"
    try:
        with pytest.raises(ValueError, match="ACCUBID_OAUTH_GRANT"):
            Config.validate()
    finally:
        Config.ACCUBID_OAUTH_GRANT = original
        Config.validate()


def test_accubid_api_url_per_area() -> None:
    """Trimble hosts each API module under its own version segment (path + casing per live API)."""
    original = (
        Config.ACCUBID_API_BASE_URL,
        Config.ACCUBID_API_VERSION_DATABASE,
        Config.ACCUBID_API_VERSION_ESTIMATE,
        Config.ACCUBID_API_VERSION_PROJECT,
        Config.ACCUBID_API_VERSION_CHANGEORDER,
        Config.ACCUBID_API_VERSION_CLOSEOUT,
    )
    try:
        Config.ACCUBID_API_BASE_URL = "https://cloud.api.trimble.com/anywhere"
        Config.ACCUBID_API_VERSION_DATABASE = "v1"
        Config.ACCUBID_API_VERSION_ESTIMATE = "v1"
        Config.ACCUBID_API_VERSION_PROJECT = "v2"
        Config.ACCUBID_API_VERSION_CHANGEORDER = "v1"
        Config.ACCUBID_API_VERSION_CLOSEOUT = "v1"
        assert (
            Config.accubid_api_url("database", "/databases")
            == "https://cloud.api.trimble.com/anywhere/database/v1/databases"
        )
        assert (
            Config.accubid_api_url("estimate", "/Estimate/x/y")
            == "https://cloud.api.trimble.com/anywhere/estimate/v1/Estimate/x/y"
        )
        assert (
            Config.accubid_api_url("project", "/Projects/db")
            == "https://cloud.api.trimble.com/anywhere/project/v2/Projects/db"
        )
        assert (
            Config.accubid_api_url("project", "/Folder")
            == "https://cloud.api.trimble.com/anywhere/project/v2/Folder"
        )
        assert (
            Config.accubid_api_url("project", "/Folders/db")
            == "https://cloud.api.trimble.com/anywhere/project/v2/Folders/db"
        )
        assert (
            Config.accubid_api_url("changeorder", "/Contracts/a/b")
            == "https://cloud.api.trimble.com/anywhere/changeorder/v1/Contracts/a/b"
        )
        assert (
            Config.accubid_api_url("closeout", "/BidBreakdownView/a/b")
            == "https://cloud.api.trimble.com/anywhere/closeout/v1/BidBreakdownView/a/b"
        )
    finally:
        (
            Config.ACCUBID_API_BASE_URL,
            Config.ACCUBID_API_VERSION_DATABASE,
            Config.ACCUBID_API_VERSION_ESTIMATE,
            Config.ACCUBID_API_VERSION_PROJECT,
            Config.ACCUBID_API_VERSION_CHANGEORDER,
            Config.ACCUBID_API_VERSION_CLOSEOUT,
        ) = original


def test_validate_rejects_bad_circuit_breaker() -> None:
    original = Config.ACCUBID_CIRCUIT_BREAKER_FAILURES
    Config.ACCUBID_CIRCUIT_BREAKER_FAILURES = 0
    try:
        with pytest.raises(ValueError, match="CIRCUIT_BREAKER_FAILURES"):
            Config.validate()
    finally:
        Config.ACCUBID_CIRCUIT_BREAKER_FAILURES = original
        Config.validate()
