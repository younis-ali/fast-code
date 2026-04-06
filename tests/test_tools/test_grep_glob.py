from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def project_dir():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "src").mkdir()
        (base / "src" / "main.py").write_text("def main():\n    print('hello')\n")
        (base / "src" / "utils.py").write_text("def helper():\n    return 42\n")
        (base / "README.md").write_text("# Project\nThis is a test project.\n")
        yield base


@pytest.mark.anyio
async def test_glob_finds_py_files(project_dir: Path):
    from app.tools.glob_tool import GlobTool

    tool = GlobTool()
    result = await tool.call({"pattern": "*.py", "path": str(project_dir)}, tool_use_id="g1")
    assert not result.is_error
    assert "main.py" in result.content
    assert "utils.py" in result.content


@pytest.mark.anyio
async def test_glob_no_match(project_dir: Path):
    from app.tools.glob_tool import GlobTool

    tool = GlobTool()
    result = await tool.call({"pattern": "*.rs", "path": str(project_dir)}, tool_use_id="g2")
    assert "No files found" in result.content


@pytest.mark.anyio
async def test_grep_finds_pattern(project_dir: Path):
    from app.tools.grep_tool import GrepTool

    tool = GrepTool()
    result = await tool.call({"pattern": "def main", "path": str(project_dir)}, tool_use_id="gr1")
    assert not result.is_error
    assert "main" in result.content


@pytest.mark.anyio
async def test_grep_no_match(project_dir: Path):
    from app.tools.grep_tool import GrepTool

    tool = GrepTool()
    result = await tool.call({"pattern": "nonexistent_pattern_xyz", "path": str(project_dir)}, tool_use_id="gr2")
    assert "No matches" in result.content or result.content.strip() == ""
