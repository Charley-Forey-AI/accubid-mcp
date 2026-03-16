"""Logging helpers for accubid MCP."""

import json
import logging
import os

from .observability import get_request_id

LOGGER_NAME = "accubid_mcp"
_configured = False


class RequestIdFilter(logging.Filter):
    """Inject request id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    """Small JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }
        return json.dumps(payload)


def setup_logging() -> None:
    """Configure logger once."""
    global _configured
    if _configured:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = (os.getenv("LOG_FORMAT") or "text").strip().lower()

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(RequestIdFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s")
        )
    logger.addHandler(handler)
    _configured = True


def get_logger() -> logging.Logger:
    """Get package logger."""
    return logging.getLogger(LOGGER_NAME)
