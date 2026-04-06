from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PermissionRule(BaseModel):
    tool: str
    action: Literal["allow", "deny"] = "allow"
    path_pattern: str = ""


class AppSettings(BaseModel):
    permissions: list[PermissionRule] = Field(default_factory=list)
    custom_system_prompt: str = ""
    default_model: str = ""
