from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_bash_echo():
    from app.tools.bash import BashTool

    tool = BashTool()
    result = await tool.call({"command": "echo hello"}, tool_use_id="test1")
    assert not result.is_error
    assert "hello" in result.content
    assert "Exit code: 0" in result.content


@pytest.mark.anyio
async def test_bash_exit_code():
    from app.tools.bash import BashTool

    tool = BashTool()
    result = await tool.call({"command": "exit 1"}, tool_use_id="test2")
    assert result.is_error
    assert "Exit code: 1" in result.content


@pytest.mark.anyio
async def test_bash_timeout():
    from app.tools.bash import BashTool

    tool = BashTool()
    result = await tool.call({"command": "sleep 10", "timeout": 1}, tool_use_id="test3")
    assert result.is_error
    assert "timed out" in result.content


@pytest.mark.anyio
async def test_bash_bad_cwd():
    from app.tools.bash import BashTool

    tool = BashTool()
    result = await tool.call(
        {"command": "ls", "working_directory": "/nonexistent_dir_12345"},
        tool_use_id="test4",
    )
    assert result.is_error
