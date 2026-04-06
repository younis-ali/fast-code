from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool

MAX_RESULTS = 2000


class GlobTool(BaseTool):
    name = "Glob"
    description = (
        "Find files matching a glob pattern. Returns matching file paths sorted by "
        "modification time. Patterns not starting with '**/' are automatically prepended "
        "with '**/' for recursive searching."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g. '*.py', '**/*.tsx', 'src/**/*.js').",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current directory).",
            },
        },
        "required": ["pattern"],
    }
    is_read_only = True

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        pattern = tool_input["pattern"]
        base_dir = Path(tool_input.get("path") or settings.work_dir or ".").resolve()

        if not base_dir.is_dir():
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Directory not found: {base_dir}",
                is_error=True,
            )

        # Auto-prepend **/ for recursive search
        if not pattern.startswith("**/"):
            pattern = f"**/{pattern}"

        matches: list[Path] = []
        try:
            for p in base_dir.glob(pattern):
                if p.is_file():
                    matches.append(p)
                    if len(matches) >= MAX_RESULTS:
                        break
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        # Sort by modification time (newest first)
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        if not matches:
            return ToolResult(tool_use_id=tool_use_id, content="No files found.")

        lines = [str(p) for p in matches]
        content = "\n".join(lines)
        if len(matches) >= MAX_RESULTS:
            content += f"\n... [capped at {MAX_RESULTS} results]"

        return ToolResult(tool_use_id=tool_use_id, content=content)


registry.register(GlobTool())
