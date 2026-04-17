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


def test_validate_rejects_invalid_oauth_grant() -> None:
    original = Config.ACCUBID_OAUTH_GRANT
    Config.ACCUBID_OAUTH_GRANT = "implicit"
    try:
        with pytest.raises(ValueError, match="ACCUBID_OAUTH_GRANT"):
            Config.validate()
    finally:
        Config.ACCUBID_OAUTH_GRANT = original
        Config.validate()


def test_validate_rejects_bad_circuit_breaker() -> None:
    original = Config.ACCUBID_CIRCUIT_BREAKER_FAILURES
    Config.ACCUBID_CIRCUIT_BREAKER_FAILURES = 0
    try:
        with pytest.raises(ValueError, match="CIRCUIT_BREAKER_FAILURES"):
            Config.validate()
    finally:
        Config.ACCUBID_CIRCUIT_BREAKER_FAILURES = original
        Config.validate()
