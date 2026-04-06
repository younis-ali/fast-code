from __future__ import annotations

import time
import uuid

from pydantic import BaseModel, Field

from app.models.messages import Message


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:16]}")
    title: str = "New Conversation"
    messages: list[Message] = Field(default_factory=list)
    model: str = ""
    system_prompt: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = time.time()

    def to_api_messages(self) -> list[dict]:
        """Return messages in Anthropic API format."""
        return [m.to_api_param() for m in self.messages]


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    model: str
    created_at: float
    updated_at: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
