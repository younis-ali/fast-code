from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult

logger = logging.getLogger(__name__)


async def execute_tool(name: str, tool_input: dict[str, Any], tool_use_id: str) -> ToolResult:
    """Execute a single tool call."""
    return await registry.execute(name, tool_input, tool_use_id)


async def execute_tools_parallel(
    tool_calls: list[dict[str, Any]],
) -> list[ToolResult]:
    """Execute multiple tool calls concurrently."""
    tasks = [
        execute_tool(
            tc["name"],
            tc.get("input", {}),
            tc.get("id", ""),
        )
        for tc in tool_calls
    ]
    return list(await asyncio.gather(*tasks))
