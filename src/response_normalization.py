"""Helpers for normalizing tool responses."""

from __future__ import annotations

import re
from typing import Any

_CAMEL_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake_case(value: str) -> str:
    """Convert key names from camel/Pascal case to snake_case."""
    normalized = _CAMEL_BOUNDARY_1.sub(r"\1_\2", value)
    normalized = _CAMEL_BOUNDARY_2.sub(r"\1_\2", normalized)
    return normalized.replace("-", "_").lower()


def normalize_keys_to_snake_case(payload: Any) -> Any:
    """Recursively normalize dictionary keys to snake_case."""
    if isinstance(payload, dict):
        return {to_snake_case(str(key)): normalize_keys_to_snake_case(val) for key, val in payload.items()}
    if isinstance(payload, list):
        return [normalize_keys_to_snake_case(item) for item in payload]
    return payload

