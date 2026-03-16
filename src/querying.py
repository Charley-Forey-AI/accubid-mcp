"""Shared list-query helpers for filtering, searching, and sorting."""

from __future__ import annotations

from typing import Any


def first_present(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return first non-None key value from a dict."""
    for key in keys:
        if key in data and data.get(key) is not None:
            return data.get(key)
    return None


def apply_search(
    items: list[Any],
    *,
    search: str | None,
    search_fields: tuple[str, ...],
) -> list[Any]:
    """Filter list items by case-insensitive search across configured fields."""
    term = (search or "").strip().lower()
    if not term:
        return items

    filtered: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            haystack = " ".join(str(item.get(field, "")).lower() for field in search_fields)
            if term in haystack:
                filtered.append(item)
        else:
            if term in str(item).lower():
                filtered.append(item)
    return filtered


def apply_equals_filter(
    items: list[Any],
    *,
    value: str | None,
    field_aliases: tuple[str, ...],
) -> list[Any]:
    """Filter dict items where any alias exactly matches value."""
    normalized = (value or "").strip().lower()
    if not normalized:
        return items

    filtered: list[Any] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate = first_present(item, field_aliases)
        if str(candidate or "").strip().lower() == normalized:
            filtered.append(item)
    return filtered


def apply_sort(
    items: list[Any],
    *,
    sort_by: str | None,
    sort_direction: str | None,
    sort_fields: dict[str, tuple[str, ...]],
) -> list[Any]:
    """Sort list items by a configured sort key alias."""
    requested_field = (sort_by or "").strip().lower()
    if not requested_field:
        return items
    aliases = sort_fields.get(requested_field)
    if not aliases:
        return items

    descending = (sort_direction or "asc").strip().lower() == "desc"

    def _sort_key(item: Any) -> tuple[int, str]:
        if not isinstance(item, dict):
            return (1, "")
        value = first_present(item, aliases)
        if value is None:
            return (1, "")
        return (0, str(value).strip().lower())

    return sorted(items, key=_sort_key, reverse=descending)
