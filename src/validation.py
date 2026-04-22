"""Input validation helpers for MCP tools."""

from __future__ import annotations

import re
from datetime import datetime

from .errors import ValidationError

_YYYYMMDD_RE = re.compile(r"^\d{8}$")
_UUID_LIKE_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
# Opaque tokens from Accubid list-databases (URL-safe base64-ish; underscores, length >> UUID)
_OPAQUE_DATABASE_TOKEN_RE = re.compile(r"^[-A-Za-z0-9_+=/]{8,512}$")


def validate_required_text(name: str, value: str, max_length: int = 256) -> str:
    """Validate required string fields used by tools."""
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(
            message=f"Invalid '{name}': value is required.",
            details={"field": name},
        )
    if len(normalized) > max_length:
        raise ValidationError(
            message=f"Invalid '{name}': max length is {max_length}.",
            details={"field": name, "max_length": max_length},
        )
    return normalized


def validate_optional_text(
    name: str,
    value: str | None,
    max_length: int = 256,
) -> str | None:
    """Validate optional string fields used by tools."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValidationError(
            message=f"Invalid '{name}': max length is {max_length}.",
            details={"field": name, "max_length": max_length},
        )
    return normalized


def validate_yyyymmdd(name: str, value: str) -> str:
    """Validate yyyymmdd date input used by due-date endpoints."""
    normalized = validate_required_text(name, value)
    if not _YYYYMMDD_RE.match(normalized):
        raise ValidationError(
            message=f"Invalid '{name}': expected yyyymmdd format.",
            details={"field": name, "expected": "yyyymmdd"},
        )
    return normalized


def validate_optional_int(
    name: str,
    value: int | None,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Validate optional integer fields."""
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValidationError(
            message=f"Invalid '{name}': expected integer.",
            details={"field": name, "expected": "int"},
        )
    if min_value is not None and value < min_value:
        raise ValidationError(
            message=f"Invalid '{name}': must be >= {min_value}.",
            details={"field": name, "min_value": min_value},
        )
    if max_value is not None and value > max_value:
        raise ValidationError(
            message=f"Invalid '{name}': must be <= {max_value}.",
            details={"field": name, "max_value": max_value},
        )
    return value


def validate_optional_int_from_any(
    name: str,
    value: int | str | None,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Validate optional integer fields, accepting int or numeric string."""
    if value is None:
        return None
    normalized: int
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        if not re.fullmatch(r"[+-]?\d+", trimmed):
            raise ValidationError(
                message=f"Invalid '{name}': expected integer.",
                details={"field": name, "expected": "int"},
            )
        normalized = int(trimmed)
    else:
        raise ValidationError(
            message=f"Invalid '{name}': expected integer.",
            details={"field": name, "expected": "int"},
        )
    return validate_optional_int(
        name,
        normalized,
        min_value=min_value,
        max_value=max_value,
    )


def normalize_yyyymmdd(name: str, value: str) -> str:
    """Normalize date string to yyyymmdd and validate."""
    normalized = validate_required_text(name, value)
    if _YYYYMMDD_RE.match(normalized):
        return normalized
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            parsed_date = datetime.strptime(normalized, fmt).date()
            return parsed_date.strftime("%Y%m%d")
        except ValueError:
            continue
    raise ValidationError(
        message=f"Invalid '{name}': expected yyyymmdd or ISO date format.",
        details={"field": name, "expected": "yyyymmdd|yyyy-mm-dd|mm/dd/yyyy"},
    )


def validate_uuid_like(name: str, value: str) -> str:
    """Validate ID values that should be UUID-like tokens."""
    normalized = validate_required_text(name, value, max_length=128)
    if not _UUID_LIKE_RE.match(normalized):
        raise ValidationError(
            message=f"Invalid '{name}': expected UUID-like identifier.",
            details={"field": name},
        )
    return normalized


def validate_database_token(name: str, value: str) -> str:
    """Validate Accubid database_token path/query parameter.

    Values may be standard UUID-shaped IDs or opaque strings returned by list-databases
    (e.g. URL-safe base64 with underscores — not UUIDs).
    """
    normalized = validate_required_text(name, value, max_length=512)
    if _UUID_LIKE_RE.match(normalized) or _OPAQUE_DATABASE_TOKEN_RE.match(normalized):
        return normalized
    raise ValidationError(
        message=f"Invalid '{name}': expected UUID or Accubid database token.",
        details={"field": name},
    )
