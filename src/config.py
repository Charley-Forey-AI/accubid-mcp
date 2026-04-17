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

    # server = client_credentials / authorization_code only (default).
    # delegated = per-request Bearer from Agent Studio / MCP (actor token); no server-stored tokens.
    # hybrid = use actor token when present, else server OAuth (client_credentials or authorization_code).
    ACCUBID_AUTH_MODE = os.getenv("ACCUBID_AUTH_MODE", "server").strip().lower()
    ACCUBID_DELEGATED_VERIFY = os.getenv("ACCUBID_DELEGATED_VERIFY", "true").strip().lower() == "true"
    ACCUBID_DELEGATED_ISSUER = os.getenv("ACCUBID_DELEGATED_ISSUER", "https://id.trimble.com").strip().rstrip("/")
    ACCUBID_DELEGATED_JWKS_URL = os.getenv("ACCUBID_DELEGATED_JWKS_URL", "").strip()
    ACCUBID_DELEGATED_AUDIENCE = os.getenv("ACCUBID_DELEGATED_AUDIENCE", "").strip()
    ACCUBID_DELEGATED_REQUIRED_SCOPES = os.getenv("ACCUBID_DELEGATED_REQUIRED_SCOPES", "").strip()
    ACCUBID_DELEGATED_JWT_LEEWAY_SECONDS = int(os.getenv("ACCUBID_DELEGATED_JWT_LEEWAY_SECONDS", "60"))
    ACCUBID_DELEGATED_RESOURCE_SERVER_URL = os.getenv("ACCUBID_DELEGATED_RESOURCE_SERVER_URL", "").strip()

    @classmethod
    def delegated_audience_list(cls) -> list[str]:
        raw = (cls.ACCUBID_DELEGATED_AUDIENCE or "").replace(",", " ")
        return [p for p in (s.strip() for s in raw.split()) if p]

    @classmethod
    def delegated_required_scopes_list(cls) -> list[str]:
        raw = (cls.ACCUBID_DELEGATED_REQUIRED_SCOPES or "").replace(",", " ")
        return [p for p in (s.strip() for s in raw.split()) if p]

    @classmethod
    def accubid_scopes(cls) -> list[str]:
        """OAuth scopes for client credentials (space- or comma-separated in ACCUBID_SCOPE)."""
        raw = (cls.ACCUBID_SCOPE or "").replace(",", " ")
        return [part for part in (s.strip() for s in raw.split()) if part]

    ACCUBID_API_BASE_URL = os.getenv(
        "ACCUBID_API_BASE_URL",
        "https://cloud.api.trimble.com/anywhere",
    ).strip().rstrip("/")
    # Per-area API versions under ACCUBID_API_BASE_URL/{area}/{version}/...
    # See https://developer.trimble.com/ — modules ship on different version paths.
    ACCUBID_API_VERSION_DATABASE = os.getenv("ACCUBID_API_VERSION_DATABASE", "v1").strip()
    ACCUBID_API_VERSION_ESTIMATE = os.getenv("ACCUBID_API_VERSION_ESTIMATE", "v2").strip()
    ACCUBID_API_VERSION_PROJECT = os.getenv("ACCUBID_API_VERSION_PROJECT", "v2").strip()
    # Folder APIs historically live on project v1 while other project routes may be v2.
    ACCUBID_API_VERSION_PROJECT_FOLDERS = os.getenv(
        "ACCUBID_API_VERSION_PROJECT_FOLDERS", "v1"
    ).strip()
    ACCUBID_API_VERSION_CHANGEORDER = os.getenv("ACCUBID_API_VERSION_CHANGEORDER", "v1").strip()
    ACCUBID_API_VERSION_CLOSEOUT = os.getenv("ACCUBID_API_VERSION_CLOSEOUT", "v1").strip()
    # Fallback for unknown area keys (should not occur for built-in tools).
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
    def accubid_api_version_for_request(cls, area: str, endpoint_path: str) -> str:
        """Return the API version segment (e.g. v1, v2) for a given area and path."""
        ep = endpoint_path or ""
        if area == "project":
            if ep.startswith("/Folder") or ep.startswith("/Folders"):
                return cls.ACCUBID_API_VERSION_PROJECT_FOLDERS or "v1"
            return cls.ACCUBID_API_VERSION_PROJECT or "v2"
        mapping = {
            "database": cls.ACCUBID_API_VERSION_DATABASE,
            "estimate": cls.ACCUBID_API_VERSION_ESTIMATE,
            "changeorder": cls.ACCUBID_API_VERSION_CHANGEORDER,
            "closeout": cls.ACCUBID_API_VERSION_CLOSEOUT,
        }
        ver = mapping.get(area, cls.ACCUBID_API_VERSION)
        return ver or "v1"

    @classmethod
    def accubid_api_url(cls, area: str, endpoint_path: str) -> str:
        """Full Trimble Accubid Anywhere URL for one request."""
        base = cls.ACCUBID_API_BASE_URL.rstrip("/")
        ver = cls.accubid_api_version_for_request(area, endpoint_path)
        path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        return f"{base}/{area}/{ver}{path}"

    @classmethod
    def _validate_server_oauth_credentials(cls) -> None:
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

    @classmethod
    def _validate_delegated_settings(cls) -> None:
        if not cls.ACCUBID_DELEGATED_VERIFY:
            return
        if not cls.ACCUBID_DELEGATED_ISSUER:
            raise ValueError("ACCUBID_DELEGATED_ISSUER is required when ACCUBID_DELEGATED_VERIFY=true")
        req = cls.delegated_required_scopes_list()
        if cls.ACCUBID_DELEGATED_REQUIRED_SCOPES and not req:
            raise ValueError("ACCUBID_DELEGATED_REQUIRED_SCOPES is set but no valid scopes were parsed.")

    @classmethod
    def validate(cls) -> None:
        """Fail fast for missing required settings."""
        if cls.ACCUBID_AUTH_MODE not in ("server", "delegated", "hybrid"):
            raise ValueError("ACCUBID_AUTH_MODE must be server, delegated, or hybrid")

        if cls.ACCUBID_AUTH_MODE == "server":
            cls._validate_server_oauth_credentials()
        elif cls.ACCUBID_AUTH_MODE == "delegated":
            cls._validate_delegated_settings()
        elif cls.ACCUBID_AUTH_MODE == "hybrid":
            cls._validate_server_oauth_credentials()
            cls._validate_delegated_settings()
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
