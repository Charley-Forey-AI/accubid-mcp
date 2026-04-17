"""Environment-backed configuration for accubid MCP."""

import os
from pathlib import Path

from dotenv import load_dotenv

from .log_config import get_logger, setup_logging

load_dotenv()
setup_logging()
logger = get_logger()


class Config:
    """Static configuration values."""

    OPENID_CONFIGURATION_URL = os.getenv(
        "OPENID_CONFIGURATION_URL",
        "https://id.trimble.com/.well-known/openid-configuration",
    ).strip()
    CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
    CLIENT_SECRET = os.getenv("CLIENT_SECRET", "").strip()
    ACCUBID_SCOPE = os.getenv("ACCUBID_SCOPE", "").strip().rstrip(",")

    # client_credentials (default) or authorization_code (user login + token file; see README).
    ACCUBID_OAUTH_GRANT = os.getenv("ACCUBID_OAUTH_GRANT", "client_credentials").strip().lower()
    OAUTH_REDIRECT_URI = os.getenv(
        "OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8765/oauth/callback",
    ).strip()
    OAUTH_TOKEN_PATH = os.getenv("OAUTH_TOKEN_PATH", "").strip()

    @classmethod
    def oauth_token_path_resolved(cls) -> Path:
        """Where user tokens are stored for ACCUBID_OAUTH_GRANT=authorization_code."""
        if cls.OAUTH_TOKEN_PATH:
            return Path(cls.OAUTH_TOKEN_PATH).expanduser()
        return Path.home() / ".accubid-mcp" / "token.json"

    @classmethod
    def accubid_scopes(cls) -> list[str]:
        """OAuth scopes for client credentials (space- or comma-separated in ACCUBID_SCOPE)."""
        raw = (cls.ACCUBID_SCOPE or "").replace(",", " ")
        return [part for part in (s.strip() for s in raw.split()) if part]

    ACCUBID_API_BASE_URL = os.getenv(
        "ACCUBID_API_BASE_URL",
        "https://cloud.api.trimble.com/anywhere",
    ).strip().rstrip("/")
    ACCUBID_API_VERSION = os.getenv("ACCUBID_API_VERSION", "v1").strip()

    ACCUBID_REQUEST_TIMEOUT_SECONDS = int(os.getenv("ACCUBID_REQUEST_TIMEOUT_SECONDS", "30"))
    ACCUBID_CLIENT_RETRY_COUNT = int(os.getenv("ACCUBID_CLIENT_RETRY_COUNT", "1"))
    ACCUBID_CLIENT_RETRY_BASE_SECONDS = float(
        os.getenv("ACCUBID_CLIENT_RETRY_BASE_SECONDS", "0.3")
    )
    ACCUBID_CLIENT_RETRY_MAX_SECONDS = float(
        os.getenv("ACCUBID_CLIENT_RETRY_MAX_SECONDS", "2.0")
    )
    ACCUBID_CLIENT_RETRYABLE_STATUS_CODES = tuple(
        int(code.strip())
        for code in os.getenv("ACCUBID_CLIENT_RETRYABLE_STATUS_CODES", "429,500,502,503,504").split(
            ","
        )
        if code.strip()
    )
    ACCUBID_CIRCUIT_BREAKER_FAILURES = int(os.getenv("ACCUBID_CIRCUIT_BREAKER_FAILURES", "5"))
    ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS = float(
        os.getenv("ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "30")
    )
    ACCUBID_RATE_LIMIT_RPS = float(os.getenv("ACCUBID_RATE_LIMIT_RPS", "0"))
    ACCUBID_LIST_DEFAULT_PAGE_SIZE = int(os.getenv("ACCUBID_LIST_DEFAULT_PAGE_SIZE", "100"))
    ACCUBID_LIST_MAX_PAGE_SIZE = int(os.getenv("ACCUBID_LIST_MAX_PAGE_SIZE", "500"))
    ACCUBID_CACHE_ENABLED = os.getenv("ACCUBID_CACHE_ENABLED", "false").strip().lower() == "true"
    ACCUBID_CACHE_TTL_SECONDS = int(os.getenv("ACCUBID_CACHE_TTL_SECONDS", "60"))
    ACCUBID_CACHE_STATE_FILE = os.getenv("ACCUBID_CACHE_STATE_FILE", "").strip()
    ACCUBID_CIRCUIT_STATE_FILE = os.getenv("ACCUBID_CIRCUIT_STATE_FILE", "").strip()
    ACCUBID_COMPOSED_TOOL_CONCURRENCY = int(os.getenv("ACCUBID_COMPOSED_TOOL_CONCURRENCY", "4"))

    # trimble-id provider returns bearer token; refresh with buffer.
    ACCUBID_TOKEN_REFRESH_BUFFER_SECONDS = int(
        os.getenv("ACCUBID_TOKEN_REFRESH_BUFFER_SECONDS", "90")
    )
    # Safe fallback TTL if token expiry metadata is unavailable.
    ACCUBID_TOKEN_TTL_SECONDS = int(os.getenv("ACCUBID_TOKEN_TTL_SECONDS", "3300"))

    HEALTHCHECK_VERIFY_DEPENDENCIES = (
        os.getenv("HEALTHCHECK_VERIFY_DEPENDENCIES", "false").strip().lower() == "true"
    )
    STARTUP_VALIDATE_DEPENDENCIES = (
        os.getenv("STARTUP_VALIDATE_DEPENDENCIES", "false").strip().lower() == "true"
    )
    STARTUP_VALIDATE_ACCUBID = (
        os.getenv("STARTUP_VALIDATE_ACCUBID", "false").strip().lower() == "true"
    )
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false").strip().lower() == "true"
    METRICS_ROUTE = os.getenv("METRICS_ROUTE", "/metrics").strip() or "/metrics"
    REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "x-request-id").strip().lower()
    ACCUBID_TOOL_NAMESPACE = os.getenv("ACCUBID_TOOL_NAMESPACE", "").strip().strip("/")
    ACCUBID_RESPONSE_SNAKE_CASE = (
        os.getenv("ACCUBID_RESPONSE_SNAKE_CASE", "false").strip().lower() == "true"
    )
    ENV = os.getenv("ENV", "development").strip().lower()
    APP_VERSION = os.getenv("APP_VERSION", "").strip()
    MCP_CORS_ORIGINS = os.getenv("MCP_CORS_ORIGINS", "").strip()
    ACCUBID_TOOLS_DISABLE_DATABASE = (
        os.getenv("ACCUBID_TOOLS_DISABLE_DATABASE", "false").strip().lower() == "true"
    )
    ACCUBID_TOOLS_DISABLE_PROJECT = (
        os.getenv("ACCUBID_TOOLS_DISABLE_PROJECT", "false").strip().lower() == "true"
    )
    ACCUBID_TOOLS_DISABLE_ESTIMATE = (
        os.getenv("ACCUBID_TOOLS_DISABLE_ESTIMATE", "false").strip().lower() == "true"
    )
    ACCUBID_TOOLS_DISABLE_CLOSEOUT = (
        os.getenv("ACCUBID_TOOLS_DISABLE_CLOSEOUT", "false").strip().lower() == "true"
    )
    ACCUBID_TOOLS_DISABLE_CHANGEORDER = (
        os.getenv("ACCUBID_TOOLS_DISABLE_CHANGEORDER", "false").strip().lower() == "true"
    )

    @classmethod
    def validate(cls) -> None:
        """Fail fast for missing required settings."""
        missing = []
        if not cls.CLIENT_ID:
            missing.append("CLIENT_ID")
        if not cls.CLIENT_SECRET:
            missing.append("CLIENT_SECRET")
        if not cls.accubid_scopes():
            missing.append("ACCUBID_SCOPE")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        if cls.ACCUBID_OAUTH_GRANT not in ("client_credentials", "authorization_code"):
            raise ValueError(
                "ACCUBID_OAUTH_GRANT must be client_credentials or authorization_code"
            )
        if cls.ACCUBID_CLIENT_RETRY_BASE_SECONDS < 0:
            raise ValueError("ACCUBID_CLIENT_RETRY_BASE_SECONDS must be >= 0")
        if cls.ACCUBID_CLIENT_RETRY_MAX_SECONDS <= 0:
            raise ValueError("ACCUBID_CLIENT_RETRY_MAX_SECONDS must be > 0")
        if cls.ACCUBID_CLIENT_RETRY_BASE_SECONDS > cls.ACCUBID_CLIENT_RETRY_MAX_SECONDS:
            raise ValueError(
                "ACCUBID_CLIENT_RETRY_BASE_SECONDS cannot exceed ACCUBID_CLIENT_RETRY_MAX_SECONDS"
            )
        if cls.ACCUBID_CIRCUIT_BREAKER_FAILURES < 1:
            raise ValueError("ACCUBID_CIRCUIT_BREAKER_FAILURES must be >= 1")
        if cls.ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS <= 0:
            raise ValueError("ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS must be > 0")
        if cls.ACCUBID_RATE_LIMIT_RPS < 0:
            raise ValueError("ACCUBID_RATE_LIMIT_RPS must be >= 0")
        if cls.ACCUBID_LIST_DEFAULT_PAGE_SIZE < 1:
            raise ValueError("ACCUBID_LIST_DEFAULT_PAGE_SIZE must be >= 1")
        if cls.ACCUBID_LIST_MAX_PAGE_SIZE < 1:
            raise ValueError("ACCUBID_LIST_MAX_PAGE_SIZE must be >= 1")
        if cls.ACCUBID_LIST_DEFAULT_PAGE_SIZE > cls.ACCUBID_LIST_MAX_PAGE_SIZE:
            raise ValueError(
                "ACCUBID_LIST_DEFAULT_PAGE_SIZE cannot exceed ACCUBID_LIST_MAX_PAGE_SIZE"
            )
        if cls.ACCUBID_CACHE_TTL_SECONDS < 0:
            raise ValueError("ACCUBID_CACHE_TTL_SECONDS must be >= 0")
        if cls.ACCUBID_COMPOSED_TOOL_CONCURRENCY < 1:
            raise ValueError("ACCUBID_COMPOSED_TOOL_CONCURRENCY must be >= 1")
        if cls.ENV == "production" and not cls.ACCUBID_API_BASE_URL.startswith("https://"):
            raise ValueError("ACCUBID_API_BASE_URL must use https:// in production")
        if not cls.ACCUBID_CLIENT_RETRYABLE_STATUS_CODES:
            logger.warning("No retryable status codes configured.")


Config.validate()
