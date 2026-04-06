from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from app.agent.state import AgentState
from app.core.approval import (
    READ_ONLY_TOOLS,
    cleanup_approval,
    create_approval_request,
    needs_approval,
)
from app.core.tool_executor import execute_tools_parallel
from app.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT = 300.0


def _tool_calls_from_ai_message(msg: AIMessage) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tc in msg.tool_calls or []:
        if not isinstance(tc, dict):
            continue
        tid = str(tc.get("id", ""))
        name = str(tc.get("name", ""))
        args = tc.get("args")
        if args is None:
            raw = tc.get("arguments")
            if isinstance(raw, str):
                try:
                    args = json.loads(raw)
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(raw, dict):
                args = raw
            else:
                args = {}
        if not isinstance(args, dict):
            args = {}
        out.append({"id": tid, "name": name, "input": args})
    return out


async def _emit_sse(config: RunnableConfig, payload: dict[str, Any]) -> None:
    emit = config.get("configurable", {}).get("emit_sse")
    if emit is not None:
        await emit(payload)


async def agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    llm = config.get("configurable", {}).get("llm")
    system_prompt = config.get("configurable", {}).get("system_prompt") or ""
    if llm is None:
        raise RuntimeError("agent_node: missing configurable llm")

    msgs: list[BaseMessage] = list(state["messages"])
    if system_prompt:
        full: list[BaseMessage] = [SystemMessage(content=system_prompt), *msgs]
    else:
        full = msgs
    response = await llm.ainvoke(full)
    return {"messages": [response]}


async def tools_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return {"messages": []}
    tool_calls = _tool_calls_from_ai_message(last)
    if not tool_calls:
        return {"messages": []}

    auto_approve = bool(config.get("configurable", {}).get("auto_approve", False))

    approved_calls = tool_calls
    if not auto_approve and needs_approval(tool_calls):
        pa = create_approval_request(tool_calls)
        await _emit_sse(
            config,
            {
                "type": "tool_approval_request",
                "request_id": pa.request_id,
                "tools": [
                    {
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                        "requires_approval": tc["name"] not in READ_ONLY_TOOLS,
                    }
                    for tc in tool_calls
                ],
            },
        )
        try:
            await asyncio.wait_for(pa.event.wait(), timeout=APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            cleanup_approval(pa.request_id)
            await _emit_sse(config, {"type": "error", "error": "Tool approval timed out (5 min)."})
            denied_msgs = [
                ToolMessage(
                    content="Tool approval timed out.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
            return {"messages": denied_msgs}

        cleanup_approval(pa.request_id)

        if not pa.approved:
            await _emit_sse(config, {"type": "tool_denied", "tool_ids": list(pa.denied_ids)})
            denied_msgs = [
                ToolMessage(
                    content="Tool execution denied by user.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
            return {"messages": denied_msgs}

        approved_calls = [tc for tc in tool_calls if tc["id"] in pa.approved_ids]
        if not approved_calls:
            denied_msgs = [
                ToolMessage(
                    content="Tool execution denied by user.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
            return {"messages": denied_msgs}

    await _emit_sse(config, {"type": "tool_execution_start", "count": len(approved_calls)})

    results = await execute_tools_parallel(approved_calls)
    tool_messages: list[ToolMessage] = []
    for result in results:
        content = result.content
        if not isinstance(content, str):
            content = json.dumps(content)
        await _emit_sse(
            config,
            {
                "type": "tool_result",
                "tool_use_id": result.tool_use_id,
                "content": content,
                "is_error": result.is_error,
            },
        )
        tm = ToolMessage(
            content=content,
            tool_call_id=result.tool_use_id,
            status="error" if result.is_error else "success",
        )
        tool_messages.append(tm)

    denied_calls = [tc for tc in tool_calls if tc not in approved_calls]
    for tc in denied_calls:
        tool_messages.append(
            ToolMessage(
                content="Tool execution denied by user.",
                tool_call_id=tc["id"],
            )
        )

    return {"messages": tool_messages}


def build_agent_graph(_registry: ToolRegistry) -> StateGraph:
    """Build uncompiled StateGraph; bind tools to the LLM per request in query_engine."""

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.set_entry_point("agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", "__end__": END},
    )
    builder.add_edge("tools", "agent")
    return builder


def compile_agent_graph(
    registry: ToolRegistry,
    *,
    checkpointer: Any | None = None,
) -> CompiledStateGraph:
    """Compile the agent graph (optionally with a checkpointer)."""
    g = build_agent_graph(registry)
    return g.compile(checkpointer=checkpointer)
