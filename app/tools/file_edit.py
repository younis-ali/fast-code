from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool


class FileEditTool(BaseTool):
    name = "Edit"
    description = (
        "Perform an exact string replacement in a file. The old_string must appear "
        "exactly once in the file (unless replace_all is true). Preserves indentation."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to modify.",
            },
            "old_string": {
                "type": "string",
                "description": "The exact text to find and replace.",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement text.",
            },
            "replace_all": {
                "type": "boolean",
                "description": "If true, replace all occurrences (default false).",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        file_path = Path(tool_input["file_path"]).resolve()
        old_string = tool_input["old_string"]
        new_string = tool_input["new_string"]
        replace_all = tool_input.get("replace_all", False)

        if not file_path.exists():
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"File not found: {file_path}",
                is_error=True,
            )
        if not file_path.is_file():
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Not a file: {file_path}",
                is_error=True,
            )

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        if old_string == new_string:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="old_string and new_string are identical; no change needed.",
                is_error=True,
            )

        count = content.count(old_string)
        if count == 0:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"old_string not found in {file_path}. Make sure it matches exactly.",
                is_error=True,
            )

        if not replace_all and count > 1:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=(
                    f"old_string appears {count} times in {file_path}. "
                    "Provide more context to make it unique, or set replace_all=true."
                ),
                is_error=True,
            )

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replaced = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replaced = 1

        try:
            file_path.write_text(new_content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        return ToolResult(
            tool_use_id=tool_use_id,
            content=f"Replaced {replaced} occurrence(s) in {file_path}",
        )


registry.register(FileEditTool())
