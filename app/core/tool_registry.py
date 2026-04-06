from __future__ import annotations

import logging
from typing import Any

from app.tools.base import BaseTool
from app.models.tools import ToolDefinition, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[ToolDefinition]:
        return [t.to_definition() for t in self._tools.values()]

    def list_api_schemas(self) -> list[dict[str, Any]]:
        return [t.to_api_schema() for t in self._tools.values()]

    async def execute(self, name: str, tool_input: dict[str, Any], tool_use_id: str = "") -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Unknown tool: {name}",
                is_error=True,
            )
        try:
            return await tool.call(tool_input, tool_use_id=tool_use_id)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Tool error: {exc}",
                is_error=True,
            )

    def discover(self) -> None:
        """Import all built-in tool modules so they register themselves."""
        from app.tools import (  # noqa: F401
            bash,
            file_read,
            file_write,
            file_edit,
            glob_tool,
            grep_tool,
            web_fetch,
            web_search,
            notebook_edit,
            todo_write,
            agent,
            coder,
        )

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


registry = ToolRegistry()
