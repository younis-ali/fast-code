from __future__ import annotations

from app.agent.tools import registry_tools_to_langchain
from app.core.chat_modes import (
    ASK_MODE_TOOL_NAMES,
    PLAN_MODE_TOOL_NAMES,
    allowed_tool_names_for_mode,
    normalize_chat_mode,
)
from app.core.coder_subtools import CODER_SUBTOOL_NAMES
from app.core.tool_registry import registry


def test_normalize_chat_mode_aliases() -> None:
    assert normalize_chat_mode("ask") == "ask"
    assert normalize_chat_mode("agent") == "agent"
    assert normalize_chat_mode("plan") == "plan"
    assert normalize_chat_mode("PLAN") == "plan"
    assert normalize_chat_mode("question") == "ask"
    assert normalize_chat_mode(None) == "agent"


def test_allowed_tools_agent_is_unrestricted() -> None:
    assert allowed_tool_names_for_mode("agent") is None


def test_ask_readonly_surface() -> None:
    ask = allowed_tool_names_for_mode("ask")
    assert ask is not None
    assert "Bash" not in ask
    assert "Write" not in ask
    assert "Read" in ask
    assert "Grep" in ask
    assert "TodoWrite" not in ask


def test_plan_mode_adds_todo_write() -> None:
    plan = allowed_tool_names_for_mode("plan")
    assert plan is not None
    assert "TodoWrite" in plan
    assert "Bash" not in plan
    assert "Write" not in plan
    assert plan == PLAN_MODE_TOOL_NAMES


def test_registry_tools_filtered_to_ask_mode() -> None:
    registry.discover()
    tools = registry_tools_to_langchain(registry, allowed_names=ASK_MODE_TOOL_NAMES)
    names = {t.name for t in tools}
    assert names == ASK_MODE_TOOL_NAMES


def test_registry_tools_filtered_to_plan_mode() -> None:
    registry.discover()
    tools = registry_tools_to_langchain(registry, allowed_names=PLAN_MODE_TOOL_NAMES)
    names = {t.name for t in tools}
    assert names == PLAN_MODE_TOOL_NAMES


def test_coder_subtools_intersect_ask_yields_readonly_only() -> None:
    ask = allowed_tool_names_for_mode("ask")
    assert ask is not None
    coder_in_ask = CODER_SUBTOOL_NAMES & ask
    assert coder_in_ask == ASK_MODE_TOOL_NAMES & CODER_SUBTOOL_NAMES
    assert "Bash" not in coder_in_ask
