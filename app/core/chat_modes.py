from __future__ import annotations

from typing import Literal

# Read-only exploration (ask + plan): no shell, no file writes, no sub-agents.
ASK_MODE_TOOL_NAMES: frozenset[str] = frozenset({
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
})

# Plan mode: read-only repo exploration plus TodoWrite to capture implementation steps.
PLAN_MODE_TOOL_NAMES: frozenset[str] = ASK_MODE_TOOL_NAMES | frozenset({"TodoWrite"})

ChatMode = Literal["ask", "agent", "plan"]


def normalize_chat_mode(value: str | ChatMode | None) -> ChatMode:
    """Normalize client input to ask | agent | plan."""
    if value in ("ask", "agent", "plan"):
        return value  # type: ignore[return-value]
    m = (str(value) if value else "agent").strip().lower()
    if m in ("ask", "question", "chat"):
        return "ask"
    if m in ("plan", "planning", "design"):
        return "plan"
    if m in ("agent", "build", "code", "edit", "run"):
        return "agent"
    return "agent"


def allowed_tool_names_for_mode(mode: ChatMode) -> frozenset[str] | None:
    """None means all registered tools; otherwise restrict to this set."""
    if mode == "agent":
        return None
    if mode == "ask":
        return ASK_MODE_TOOL_NAMES
    if mode == "plan":
        return PLAN_MODE_TOOL_NAMES
    return None
