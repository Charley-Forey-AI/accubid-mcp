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


def test_accubid_api_url_per_area_and_project_folders() -> None:
    """Trimble hosts each API module under its own version segment."""
    original = (
        Config.ACCUBID_API_BASE_URL,
        Config.ACCUBID_API_VERSION_DATABASE,
        Config.ACCUBID_API_VERSION_ESTIMATE,
        Config.ACCUBID_API_VERSION_PROJECT,
        Config.ACCUBID_API_VERSION_PROJECT_FOLDERS,
        Config.ACCUBID_API_VERSION_CHANGEORDER,
        Config.ACCUBID_API_VERSION_CLOSEOUT,
    )
    try:
        Config.ACCUBID_API_BASE_URL = "https://cloud.api.trimble.com/anywhere"
        Config.ACCUBID_API_VERSION_DATABASE = "v1"
        Config.ACCUBID_API_VERSION_ESTIMATE = "v2"
        Config.ACCUBID_API_VERSION_PROJECT = "v2"
        Config.ACCUBID_API_VERSION_PROJECT_FOLDERS = "v1"
        Config.ACCUBID_API_VERSION_CHANGEORDER = "v1"
        Config.ACCUBID_API_VERSION_CLOSEOUT = "v1"
        assert (
            Config.accubid_api_url("database", "/Databases")
            == "https://cloud.api.trimble.com/anywhere/database/v1/Databases"
        )
        assert (
            Config.accubid_api_url("estimate", "/Estimates/x/y")
            == "https://cloud.api.trimble.com/anywhere/estimate/v2/Estimates/x/y"
        )
        assert (
            Config.accubid_api_url("project", "/Projects/db")
            == "https://cloud.api.trimble.com/anywhere/project/v2/Projects/db"
        )
        assert (
            Config.accubid_api_url("project", "/Folder")
            == "https://cloud.api.trimble.com/anywhere/project/v1/Folder"
        )
        assert (
            Config.accubid_api_url("project", "/Folders/db")
            == "https://cloud.api.trimble.com/anywhere/project/v1/Folders/db"
        )
        assert (
            Config.accubid_api_url("changeorder", "/Contracts/a/b")
            == "https://cloud.api.trimble.com/anywhere/changeorder/v1/Contracts/a/b"
        )
        assert (
            Config.accubid_api_url("closeout", "/FinalPrice/a/b")
            == "https://cloud.api.trimble.com/anywhere/closeout/v1/FinalPrice/a/b"
        )
    finally:
        (
            Config.ACCUBID_API_BASE_URL,
            Config.ACCUBID_API_VERSION_DATABASE,
            Config.ACCUBID_API_VERSION_ESTIMATE,
            Config.ACCUBID_API_VERSION_PROJECT,
            Config.ACCUBID_API_VERSION_PROJECT_FOLDERS,
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
