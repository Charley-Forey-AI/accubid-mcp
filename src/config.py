"""Environment-backed configuration for accubid MCP."""

import os
from pathlib import Path

from dotenv import load_dotenv

from .log_config import get_logger, setup_logging

# Resolve repo `.env` regardless of process cwd (systemd WorkingDirectory quirks).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def env_truthy(name: str, *, default: bool = False) -> bool:
    """Parse booleans from env; accepts 1/true/yes/on and strips simple quotes."""
    raw = os.getenv(name)
    if raw is None:
        return default
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    return v.lower() in ("1", "true", "yes", "on")


load_dotenv(_PROJECT_ROOT / ".env")
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
    ACCUBID_SCOPE = os.getenv("ACCUBID_SCOPE", "openid accubid_agentic_ai").strip().rstrip(",")

    ACCUBID_API_BASE_URL = os.getenv(
        "ACCUBID_API_BASE_URL",
        "https://cloud.api.trimble.com/anywhere",
    ).strip().rstrip("/")
    ACCUBID_API_VERSION_DATABASE = os.getenv("ACCUBID_API_VERSION_DATABASE", "v1").strip()
    ACCUBID_API_VERSION_ESTIMATE = os.getenv("ACCUBID_API_VERSION_ESTIMATE", "v1").strip()
    ACCUBID_API_VERSION_PROJECT = os.getenv("ACCUBID_API_VERSION_PROJECT", "v2").strip()
    ACCUBID_API_VERSION_CHANGEORDER = os.getenv("ACCUBID_API_VERSION_CHANGEORDER", "v1").strip()
    ACCUBID_API_VERSION_CLOSEOUT = os.getenv("ACCUBID_API_VERSION_CLOSEOUT", "v1").strip()
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
    def debug_log_outbound_token(cls) -> bool:
        """Logs full bearer on each Accubid HTTP call when true; reads env each time."""
        return env_truthy("ACCUBID_DEBUG_LOG_OUTBOUND_TOKEN")

    @classmethod
    def token_exchange_resource(cls) -> str | None:
        """Optional RFC 8707 `resource` URI sent to Trimble token exchange (unset when empty)."""
        r = os.getenv("ACCUBID_TOKEN_EXCHANGE_RESOURCE", "").strip()
        return r or None

    @classmethod
    def token_exchange_audience(cls) -> str | None:
        """Optional `audience` sent to Trimble token exchange (some IdPs require API audience GUID)."""
        a = os.getenv("ACCUBID_TOKEN_EXCHANGE_AUDIENCE", "").strip()
        return a or None

    @classmethod
    def scope_string(cls) -> str:
        """Space-separated OAuth scope string for token exchange."""
        return " ".join(cls.accubid_scopes())

    @classmethod
    def accubid_scopes(cls) -> list[str]:
        """OAuth scopes (space- or comma-separated in ACCUBID_SCOPE)."""
        raw = (cls.ACCUBID_SCOPE or "").replace(",", " ")
        return [part for part in (s.strip() for s in raw.split()) if part]

    @classmethod
    def accubid_api_version_for_request(cls, area: str, _endpoint_path: str) -> str:
        """Return the API version segment (e.g. v1, v2) for a given area and path."""
        mapping = {
            "database": cls.ACCUBID_API_VERSION_DATABASE,
            "estimate": cls.ACCUBID_API_VERSION_ESTIMATE,
            "project": cls.ACCUBID_API_VERSION_PROJECT,
            "changeorder": cls.ACCUBID_API_VERSION_CHANGEORDER,
            "closeout": cls.ACCUBID_API_VERSION_CLOSEOUT,
        }
        ver = mapping.get(area, cls.ACCUBID_API_VERSION)
        if area == "project":
            return ver or "v2"
        return ver or "v1"

    @classmethod
    def accubid_api_url(cls, area: str, endpoint_path: str) -> str:
        """Full Trimble Accubid Anywhere URL for one request."""
        base = cls.ACCUBID_API_BASE_URL.rstrip("/")
        ver = cls.accubid_api_version_for_request(area, endpoint_path)
        path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        return f"{base}/{area}/{ver}{path}"

    @classmethod
    def _validate_obo_credentials(cls) -> None:
        missing: list[str] = []
        if not cls.CLIENT_ID:
            missing.append("CLIENT_ID")
        if not cls.CLIENT_SECRET:
            missing.append("CLIENT_SECRET")
        if not cls.accubid_scopes():
            missing.append("ACCUBID_SCOPE")
        if missing:
            raise ValueError(
                "Trimble on-behalf-of token exchange requires: " + ", ".join(missing)
            )

    @classmethod
    def validate(cls) -> None:
        """Fail fast for missing required settings."""
        cls._validate_obo_credentials()
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
