from __future__ import annotations

import abc
from typing import Any

from app.models.tools import ToolDefinition, ToolResult


class BaseTool(abc.ABC):
    """Every tool must subclass this and implement the abstract members."""

    name: str
    description: str
    input_schema: dict[str, Any]
    is_read_only: bool = False

    @abc.abstractmethod
    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        """Execute the tool and return a ToolResult."""

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            is_read_only=self.is_read_only,
        )

    def to_api_schema(self) -> dict[str, Any]:
        """Return the Anthropic tool-use schema dict."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
