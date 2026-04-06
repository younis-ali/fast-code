from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    is_read_only: bool = False
    is_enabled: bool = True


class ToolResult(BaseModel):
    tool_use_id: str
    content: str | list[dict[str, Any]] = ""
    is_error: bool = False

    def to_api_param(self) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            "is_error": self.is_error,
        }
