"""Shared pagination helpers for list-style tool responses."""

from __future__ import annotations

from typing import Any

from .config import Config
from .validation import validate_optional_int_from_any


def normalize_list(data: Any) -> list[Any]:
    """Normalize API payload into a list."""
    return data if isinstance(data, list) else [data]


def paginate_items(
    items: list[Any],
    *,
    page_index: int | str | None,
    page_size: int | str | None,
) -> dict[str, Any]:
    """Apply client-side pagination and include standard metadata."""
    normalized_page_index = validate_optional_int_from_any("page_index", page_index, min_value=0) or 0
    normalized_page_size = (
        validate_optional_int_from_any(
            "page_size",
            page_size,
            min_value=1,
            max_value=Config.ACCUBID_LIST_MAX_PAGE_SIZE,
        )
        or Config.ACCUBID_LIST_DEFAULT_PAGE_SIZE
    )

    total_count = len(items)
    start = normalized_page_index * normalized_page_size
    end = start + normalized_page_size
    paged_items = items[start:end]
    total_pages = (total_count + normalized_page_size - 1) // normalized_page_size if total_count > 0 else 0

    return {
        "items": paged_items,
        "pagination": {
            "page_index": normalized_page_index,
            "page_size": normalized_page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next_page": end < total_count,
        },
    }
