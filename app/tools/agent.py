from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.llm import get_chat_model
from app.agent.runtime import get_compiled_graph
from app.agent.tools import registry_tools_to_langchain
from app.config import settings
from app.core.chat_context import get_chat_mode
from app.core.chat_modes import allowed_tool_names_for_mode
from app.core.prompt_builder import build_system_prompt
from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _extract_assistant_text(messages: list[Any]) -> str:
    parts: list[str] = []
    for m in messages:
        if isinstance(m, AIMessage) and m.content:
            c = m.content
            if isinstance(c, str) and c.strip():
                parts.append(c)
    return "\n".join(parts) if parts else ""


class AgentTool(BaseTool):
    name = "Agent"
    description = (
        "Launch a sub-agent to handle a complex, multi-step task. The sub-agent gets "
        "its own conversation context and tool access. Returns the agent's final response."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed task description for the sub-agent.",
            },
            "description": {
                "type": "string",
                "description": "Short 3-5 word description of what the agent will do.",
            },
            "model": {
                "type": "string",
                "description": "Optional model override for the sub-agent.",
            },
        },
        "required": ["prompt", "description"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        prompt = tool_input["prompt"]
        model_override = tool_input.get("model")
        sub_model = model_override or settings.anthropic_model or settings.openai_model

        try:
            graph = get_compiled_graph()
            mode = get_chat_mode()
            allowed = allowed_tool_names_for_mode(mode)
            lc_tools = registry_tools_to_langchain(registry, allowed_names=allowed)
            llm = get_chat_model(sub_model, max_tokens=8192).bind_tools(lc_tools)
            system_prompt = build_system_prompt(mode=mode)
            config: dict[str, Any] = {
                "configurable": {
                    "llm": llm,
                    "system_prompt": system_prompt,
                    "auto_approve": True,
                },
                "recursion_limit": 100,
            }
            out = await graph.ainvoke(
                {"messages": [HumanMessage(content=prompt)]},
                config,
            )
            msgs = list(out.get("messages", []))
            text = _extract_assistant_text(msgs)
            return ToolResult(
                tool_use_id=tool_use_id,
                content=text if text else "(Agent completed with no text output)",
            )

        except Exception as exc:
            logger.exception("Sub-agent failed")
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Sub-agent error: {exc}",
                is_error=True,
            )


registry.register(AgentTool())
