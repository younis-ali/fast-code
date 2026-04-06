from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool


class FileWriteTool(BaseTool):
    name = "Write"
    description = (
        "Write content to a file. Creates the file and any parent directories if they "
        "don't exist. Overwrites the file if it already exists."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to write.",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file.",
            },
        },
        "required": ["file_path", "content"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        file_path = Path(tool_input["file_path"]).resolve()
        content = tool_input["content"]

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        return ToolResult(
            tool_use_id=tool_use_id,
            content=f"Wrote {len(content)} bytes to {file_path}",
        )


registry.register(FileWriteTool())
