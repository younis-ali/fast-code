from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.llm import get_chat_model
from app.agent.runtime import get_compiled_graph
from app.agent.tools import base_tool_to_structured_tool
from app.config import settings
from app.core.chat_context import get_chat_mode
from app.core.chat_modes import allowed_tool_names_for_mode
from app.core.coder_subtools import CODER_SUBTOOL_NAMES
from app.core.prompt_builder import build_coder_system_prompt
from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

MAX_CODER_TURNS = 25


def _coder_tool_schemas() -> list[dict[str, Any]]:
    """Anthropic-style tool schemas for the Coder sub-tool set (tests / introspection)."""
    out: list[dict[str, Any]] = []
    for name in sorted(CODER_SUBTOOL_NAMES):
        t = registry.get(name)
        if t is not None:
            out.append(t.to_api_schema())
    return out


def _coder_langchain_tools() -> list[Any]:
    mode = get_chat_mode()
    allowed = allowed_tool_names_for_mode(mode)
    if allowed is None:
        names = sorted(CODER_SUBTOOL_NAMES)
    else:
        names = sorted(CODER_SUBTOOL_NAMES & allowed)
    out: list[Any] = []
    for name in names:
        t = registry.get(name)
        if t is not None:
            out.append(base_tool_to_structured_tool(t))
    return out


def _extract_assistant_text(messages: list[Any]) -> str:
    parts: list[str] = []
    for m in messages:
        if isinstance(m, AIMessage) and m.content:
            c = m.content
            if isinstance(c, str) and c.strip():
                parts.append(c)
    return "\n".join(parts) if parts else ""


class CoderTool(BaseTool):
    name = "Coder"
    description = (
        "Use this for substantial coding work: implementing features, fixing bugs, "
        "refactoring, adding tests, or changing multiple files. Runs a dedicated "
        "coding sub-agent with file and shell tools only (no nested agents). "
        "Prefer this over Agent when the task is specifically about editing code in the repo."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Detailed implementation task: what to build or fix, constraints, "
                    "and files or areas to touch if known."
                ),
            },
            "description": {
                "type": "string",
                "description": "Short 3-7 word label for this coding task.",
            },
            "model": {
                "type": "string",
                "description": "Optional model id for this coding run (defaults to main model).",
            },
        },
        "required": ["prompt", "description"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        prompt = tool_input["prompt"]
        model_override = tool_input.get("model")
        sub_model = model_override or settings.anthropic_model or settings.openai_model

        try:
            tool_objs = _coder_langchain_tools()
            if not tool_objs:
                return ToolResult(
                    tool_use_id=tool_use_id,
                    content="Coder tool: no sub-tools registered in registry.",
                    is_error=True,
                )

            graph = get_compiled_graph()
            llm = get_chat_model(sub_model, max_tokens=8192).bind_tools(tool_objs)
            system_prompt = build_coder_system_prompt()
            config: dict[str, Any] = {
                "configurable": {
                    "llm": llm,
                    "system_prompt": system_prompt,
                    "auto_approve": True,
                },
                "recursion_limit": MAX_CODER_TURNS,
            }
            out = await graph.ainvoke(
                {"messages": [HumanMessage(content=prompt)]},
                config,
            )
            msgs = list(out.get("messages", []))
            summary = _extract_assistant_text(msgs)
            if not summary:
                summary = "(Coder finished with no text output)"
            logger.info("Coder sub-agent completed: model=%s", sub_model)
            return ToolResult(tool_use_id=tool_use_id, content=summary)

        except Exception as exc:
            logger.exception("Coder sub-agent failed")
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Coder error: {exc}",
                is_error=True,
            )


registry.register(CoderTool())
