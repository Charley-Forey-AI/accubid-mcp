from src.registry import get_registry, load_capabilities, search_tools


def test_registry_loads_tools() -> None:
    tools = get_registry()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_search_tools_by_domain() -> None:
    tools = search_tools(domain="database")
    assert tools
    assert all(tool.get("domain") == "database" for tool in tools)


def test_capabilities_has_tool_domains() -> None:
    caps = load_capabilities()
    assert "tools_domains" in caps
