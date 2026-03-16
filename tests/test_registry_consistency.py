from src.main import list_available_tools
from src.registry import HANDLER_REGISTRY, get_registry, load_capabilities


def test_capabilities_tool_count_matches_registry() -> None:
    caps = load_capabilities()
    assert caps.get("tool_count") == len(get_registry())


def test_registry_contains_runtime_handlers() -> None:
    registry_names = {tool.get("name") for tool in get_registry()}
    runtime_tools = {name for name in HANDLER_REGISTRY if "/" not in name}
    runtime_tools.add("list_available_tools")
    assert runtime_tools.issubset(registry_names)


def test_runtime_registry_keeps_list_available_tools() -> None:
    assert callable(list_available_tools.fn)
