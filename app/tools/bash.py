from __future__ import annotations

import os
from typing import Any

from app.config import settings
from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool
from app.utils.subprocess import run_command


class BashTool(BaseTool):
    name = "Bash"
    description = (
        "Run a shell command. The command is executed in a bash shell with a configurable "
        "timeout (default 30s). Returns stdout, stderr, and the exit code."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "number",
                "description": "Maximum execution time in seconds (default 30).",
            },
            "description": {
                "type": "string",
                "description": "Short description of what the command does (5-10 words).",
            },
            "working_directory": {
                "type": "string",
                "description": "Absolute path to run the command in.",
            },
        },
        "required": ["command"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        command = tool_input["command"]
        timeout = tool_input.get("timeout", 120.0)
        cwd = tool_input.get("working_directory") or settings.work_dir or None

        if cwd and not os.path.isdir(cwd):
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Working directory does not exist: {cwd}",
                is_error=True,
            )

        result = await run_command(command, cwd=cwd, timeout=timeout)

        parts: list[str] = []
        if result.stdout:
            parts.append(result.stdout)
        if result.stderr:
            parts.append(f"STDERR:\n{result.stderr}")
        if result.timed_out:
            parts.append(f"[timed out after {timeout}s]")

        parts.append(f"Exit code: {result.returncode}")

        content = "\n".join(parts)
        # Cap output to avoid blowing context
        if len(content) > 100_000:
            content = content[:100_000] + "\n... [output truncated]"

        return ToolResult(
            tool_use_id=tool_use_id,
            content=content,
            is_error=result.returncode != 0,
        )


registry.register(BashTool())
