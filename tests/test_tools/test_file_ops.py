from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.mark.anyio
async def test_write_and_read(tmp_dir: Path):
    from app.tools.file_write import FileWriteTool
    from app.tools.file_read import FileReadTool

    writer = FileWriteTool()
    reader = FileReadTool()

    fp = str(tmp_dir / "test.txt")
    content = "line one\nline two\nline three\n"

    # Write
    result = await writer.call({"file_path": fp, "content": content}, tool_use_id="w1")
    assert not result.is_error
    assert "Wrote" in result.content

    # Read
    result = await reader.call({"file_path": fp}, tool_use_id="r1")
    assert not result.is_error
    assert "line one" in result.content
    assert "line two" in result.content

    # Read with offset/limit
    result = await reader.call({"file_path": fp, "offset": 2, "limit": 1}, tool_use_id="r2")
    assert not result.is_error
    assert "line two" in result.content
    assert "line one" not in result.content


@pytest.mark.anyio
async def test_read_nonexistent():
    from app.tools.file_read import FileReadTool

    reader = FileReadTool()
    result = await reader.call({"file_path": "/nonexistent_12345.txt"}, tool_use_id="r3")
    assert result.is_error


@pytest.mark.anyio
async def test_edit(tmp_dir: Path):
    from app.tools.file_write import FileWriteTool
    from app.tools.file_edit import FileEditTool
    from app.tools.file_read import FileReadTool

    writer = FileWriteTool()
    editor = FileEditTool()
    reader = FileReadTool()

    fp = str(tmp_dir / "edit_test.py")
    await writer.call({"file_path": fp, "content": "def hello():\n    return 'world'\n"}, tool_use_id="w")

    # Edit
    result = await editor.call({
        "file_path": fp,
        "old_string": "return 'world'",
        "new_string": "return 'universe'",
    }, tool_use_id="e1")
    assert not result.is_error
    assert "Replaced 1" in result.content

    # Verify
    result = await reader.call({"file_path": fp}, tool_use_id="r")
    assert "universe" in result.content
    assert "world" not in result.content


@pytest.mark.anyio
async def test_edit_not_found(tmp_dir: Path):
    from app.tools.file_write import FileWriteTool
    from app.tools.file_edit import FileEditTool

    writer = FileWriteTool()
    editor = FileEditTool()

    fp = str(tmp_dir / "edit_nf.py")
    await writer.call({"file_path": fp, "content": "abc"}, tool_use_id="w")

    result = await editor.call({
        "file_path": fp,
        "old_string": "xyz",
        "new_string": "123",
    }, tool_use_id="e")
    assert result.is_error
    assert "not found" in result.content
