from __future__ import annotations

import shutil
from typing import Any

from app.config import settings
from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool
from app.utils.subprocess import run_command


class GrepTool(BaseTool):
    name = "Grep"
    description = (
        "Search file contents using regex patterns. Uses ripgrep (rg) when available for "
        "speed, with fallback to grep. Supports context lines, file type filtering, "
        "glob patterns, and multiple output modes."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for.",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (default: current directory).",
            },
            "glob": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g. '*.py').",
            },
            "type": {
                "type": "string",
                "description": "File type to search (rg --type), e.g. 'py', 'js', 'rust'.",
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
                "description": "Output mode (default: content).",
            },
            "-A": {"type": "integer", "description": "Lines to show after each match."},
            "-B": {"type": "integer", "description": "Lines to show before each match."},
            "-C": {"type": "integer", "description": "Lines of context around each match."},
            "-i": {"type": "boolean", "description": "Case insensitive search."},
            "multiline": {"type": "boolean", "description": "Enable multiline matching."},
            "head_limit": {"type": "integer", "description": "Limit number of matches shown."},
        },
        "required": ["pattern"],
    }
    is_read_only = True

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        pattern = tool_input["pattern"]
        path = tool_input.get("path") or settings.work_dir or "."
        output_mode = tool_input.get("output_mode", "content")

        has_rg = shutil.which("rg") is not None
        exe = "rg" if has_rg else "grep"

        args: list[str] = [exe]

        if has_rg:
            args.append("--no-heading")
            args.append("--line-number")
            args.append("--color=never")

            if tool_input.get("-i"):
                args.append("-i")
            if tool_input.get("multiline"):
                args.extend(["-U", "--multiline-dotall"])
            if tool_input.get("glob"):
                args.extend(["--glob", tool_input["glob"]])
            if tool_input.get("type"):
                args.extend(["--type", tool_input["type"]])

            ctx = tool_input.get("-C")
            if ctx:
                args.extend(["-C", str(ctx)])
            else:
                a = tool_input.get("-A")
                b = tool_input.get("-B")
                if a:
                    args.extend(["-A", str(a)])
                if b:
                    args.extend(["-B", str(b)])

            if output_mode == "files_with_matches":
                args.append("-l")
            elif output_mode == "count":
                args.append("-c")

            head_limit = tool_input.get("head_limit")
            if head_limit and output_mode == "content":
                args.extend(["-m", str(head_limit)])
        else:
            # grep fallback
            args.extend(["-rn", "--color=never"])
            if tool_input.get("-i"):
                args.append("-i")
            if output_mode == "files_with_matches":
                args.append("-l")
            elif output_mode == "count":
                args.append("-c")

        args.append("--")
        args.append(pattern)
        args.append(path)

        cmd = " ".join(_shell_quote(a) for a in args)
        result = await run_command(cmd, timeout=30.0)

        output = result.stdout.strip()
        if not output and result.returncode in (0, 1):
            return ToolResult(tool_use_id=tool_use_id, content="No matches found.")

        if len(output) > 150_000:
            output = output[:150_000] + "\n... [output truncated]"

        return ToolResult(
            tool_use_id=tool_use_id,
            content=output,
            is_error=result.returncode not in (0, 1),
        )


def _shell_quote(s: str) -> str:
    if " " in s or "'" in s or '"' in s or "\\" in s or any(c in s for c in "&|;()$`!"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


registry.register(GrepTool())
