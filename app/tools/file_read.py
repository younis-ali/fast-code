from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool
from app.utils.paths import IMAGE_EXTENSIONS, is_text_file


class FileReadTool(BaseTool):
    name = "Read"
    description = (
        "Read a file from the filesystem. Supports text files with optional line offset/limit, "
        "images (returned as base64), and binary detection. Lines are numbered in output."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to read.",
            },
            "offset": {
                "type": "integer",
                "description": "1-based line number to start reading from. Negative counts from end.",
            },
            "limit": {
                "type": "integer",
                "description": "Number of lines to read.",
            },
        },
        "required": ["file_path"],
    }
    is_read_only = True

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        file_path = Path(tool_input["file_path"]).resolve()
        offset = tool_input.get("offset")
        limit = tool_input.get("limit")

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

        # Image files
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            data = base64.b64encode(file_path.read_bytes()).decode()
            media_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            return ToolResult(
                tool_use_id=tool_use_id,
                content=[{
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_map.get(file_path.suffix.lower(), "application/octet-stream"),
                        "data": data,
                    },
                }],
            )

        if not is_text_file(file_path):
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Binary file, not readable as text: {file_path}",
                is_error=True,
            )

        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        if not text:
            return ToolResult(tool_use_id=tool_use_id, content="File is empty.")

        lines = text.splitlines(keepends=True)
        total = len(lines)

        if offset is not None:
            if offset < 0:
                start = max(0, total + offset)
            else:
                start = max(0, offset - 1)  # 1-based to 0-based
        else:
            start = 0

        if limit is not None:
            end = min(total, start + limit)
        else:
            end = total

        selected = lines[start:end]

        # Number lines
        numbered = []
        for i, line in enumerate(selected, start=start + 1):
            numbered.append(f"{i:6d}|{line.rstrip()}")

        content = "\n".join(numbered)
        if len(content) > 200_000:
            content = content[:200_000] + "\n... [truncated]"

        return ToolResult(tool_use_id=tool_use_id, content=content)


registry.register(FileReadTool())
