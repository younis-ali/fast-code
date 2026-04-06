from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_mcp_list_tools():
    from mcp_explorer.server import mcp

    tools = await mcp.list_tools()
    assert len(tools) == 8
    names = [t.name for t in tools]
    assert "list_source_files" in names
    assert "read_source_file" in names
    assert "search_source" in names
    assert "get_architecture" in names


@pytest.mark.anyio
async def test_mcp_list_directory():
    from mcp_explorer.server import list_directory

    result = list_directory("")
    assert isinstance(result, str)
    # Should list contents of the app/ directory (default SRC_ROOT)
    assert len(result) > 0


@pytest.mark.anyio
async def test_mcp_get_file_info():
    from mcp_explorer.server import get_file_info

    result = get_file_info("__init__.py")
    assert "Path:" in result
    assert "Size:" in result
