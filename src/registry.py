"""Tool registry helpers from YAML metadata."""

import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_YAML_DIR = Path(__file__).parent / "yaml"
_REGISTRY_PATH = _YAML_DIR / "tool_registry.yaml"
_CAPABILITIES_PATH = _YAML_DIR / "capabilities.yaml"
_CACHE: Optional[List[Dict[str, Any]]] = None

HANDLER_REGISTRY: Dict[str, Any] = {}


def load_registry() -> List[Dict[str, Any]]:
    """Load tool metadata from YAML."""
    if not _REGISTRY_PATH.exists():
        return []
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    tools = data.get("tools", [])
    return tools if isinstance(tools, list) else []


def get_registry() -> List[Dict[str, Any]]:
    """Cached tool metadata list."""
    global _CACHE
    if _CACHE is None:
        _CACHE = load_registry()
    return _CACHE


def search_tools(query: Optional[str] = None, domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search tool metadata by query/domain."""
    tools = build_runtime_registry()
    if domain:
        d = domain.strip().lower()
        tools = [t for t in tools if (t.get("domain") or "").strip().lower() == d]
    if not query:
        return tools
    terms = [s.strip().lower() for s in query.split() if s.strip()]
    if not terms:
        return tools
    result: List[Dict[str, Any]] = []
    for tool in tools:
        haystack = " ".join(
            [
                str(tool.get("name", "")).lower(),
                str(tool.get("description", "")).lower(),
                str(tool.get("when_to_use", "")).lower(),
                " ".join(str(k).lower() for k in tool.get("keywords", [])),
                " ".join(str(k).lower() for k in tool.get("runtime", {}).get("required_params", [])),
                " ".join(str(k).lower() for k in tool.get("runtime", {}).get("optional_params", [])),
            ]
        )
        if any(term in haystack for term in terms):
            result.append(tool)
    return result


def _extract_callable(handler: Any) -> Any:
    if handler is None:
        return None
    return getattr(handler, "fn", handler)


def _signature_summary(handler: Any) -> dict[str, Any]:
    fn = _extract_callable(handler)
    if fn is None:
        return {"required_params": [], "optional_params": []}
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return {"required_params": [], "optional_params": []}

    required_params: list[str] = []
    optional_params: list[str] = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if param.default is inspect._empty:
            required_params.append(name)
        else:
            optional_params.append(name)
    return {"required_params": required_params, "optional_params": optional_params}


def build_runtime_registry(extra_handlers: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Merge YAML registry metadata with currently registered runtime handlers."""
    base_tools = get_registry()
    by_name = {str(tool.get("name")): dict(tool) for tool in base_tools if isinstance(tool, dict)}
    handlers = dict(HANDLER_REGISTRY)
    handlers.update(extra_handlers or {})
    entries: list[dict[str, Any]] = []

    for tool_name, handler in handlers.items():
        if not isinstance(tool_name, str):
            continue
        entry = by_name.get(tool_name)
        if entry is None and "/" in tool_name:
            _, maybe_base_name = tool_name.split("/", 1)
            base_entry = by_name.get(maybe_base_name)
            if base_entry is not None:
                entry = dict(base_entry)
        if entry is None:
            entry = {
                "name": tool_name,
                "action_type": "read",
                "domain": "system",
                "description": "Runtime-registered tool.",
                "keywords": [],
            }
        entry["name"] = tool_name
        runtime_meta = _signature_summary(handler)
        runtime_meta["registered"] = True
        runtime_meta["namespaced_alias"] = "/" in tool_name
        entry["runtime"] = runtime_meta
        entries.append(entry)

    # Include YAML-only tools that may be disabled at runtime.
    existing_names = {entry.get("name") for entry in entries}
    for tool in base_tools:
        name = tool.get("name")
        if name in existing_names:
            continue
        item = dict(tool)
        item["runtime"] = {
            "registered": False,
            "namespaced_alias": False,
            "required_params": [],
            "optional_params": [],
        }
        entries.append(item)
    return sorted(entries, key=lambda item: str(item.get("name", "")))


def load_capabilities() -> Dict[str, Any]:
    """Load server capabilities from YAML."""
    if not _CAPABILITIES_PATH.exists():
        return {}
    with open(_CAPABILITIES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    caps = data.get("capabilities", {})
    if not isinstance(caps, dict):
        return {}
    runtime_tool_count = len({name for name in HANDLER_REGISTRY if "/" not in name})
    if runtime_tool_count:
        caps["runtime_tool_count"] = runtime_tool_count + 1  # includes list_available_tools
    return caps
