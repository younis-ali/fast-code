from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    model: str = ""
    system_prompt: str = ""
    tools_enabled: list[str] = Field(default_factory=list)
    max_turns: int = 100
    working_directory: str = ""


class Session(BaseModel):
    id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:16]}")
    conversation_id: str = ""
    config: SessionConfig = Field(default_factory=SessionConfig)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
