from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    source: dict[str, Any]


class ToolUseContent(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str = Field(default_factory=lambda: f"toolu_{uuid.uuid4().hex[:24]}")
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResultContent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | list[dict[str, Any]] = ""
    is_error: bool = False


ContentBlock = TextContent | ImageContent | ToolUseContent | ToolResultContent


class Message(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:24]}")
    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]
    created_at: float = Field(default_factory=time.time)

    def to_api_param(self) -> dict[str, Any]:
        """Convert to Anthropic API message format."""
        return {"role": self.role, "content": self.content}
