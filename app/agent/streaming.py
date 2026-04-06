"""Helpers for streaming the LangGraph agent with SSE approval events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langgraph.graph.state import CompiledStateGraph

from app.core.approval import READ_ONLY_TOOLS
from app.utils.streaming import sse_done, sse_event

logger = logging.getLogger(__name__)


def _text_from_chunk(chunk: AIMessageChunk) -> str:
    c = chunk.content
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return ""


def _emit_tool_calls_from_ai(msg: AIMessage, auto_approve: bool) -> list[dict[str, Any]]:
    """Build tool_use_start / tool_use_end SSE payloads from a completed AIMessage."""
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
        out.append({"type": "tool_use_start", "id": tid, "name": name})
        out.append({
            "type": "tool_use_end",
            "id": tid,
            "name": name,
            "input": args,
            "requires_approval": (not auto_approve) and name not in READ_ONLY_TOOLS,
        })
    return out


async def stream_compiled_graph(
    graph: CompiledStateGraph,
    input_state: dict[str, Any],
    config: dict[str, Any],
    *,
    conversation_id: str,
    model: str,
    auto_approve: bool,
    out_messages: list[BaseMessage] | None = None,
    chat_mode: str | None = None,
) -> AsyncIterator[str]:
    """
    Run graph with astream (messages + values), merge approval SSE from tools node,
    and yield SSE strings for the chat client.
    """
    q: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()

    async def emit_sse(payload: dict[str, Any]) -> None:
        await q.put(("sse", payload))

    cfg = dict(config)
    cfg.setdefault("configurable", {})
    cfg["configurable"]["emit_sse"] = emit_sse

    seen_tool_sig: set[str] = set()

    async def producer() -> None:
        try:
            async for mode, chunk in graph.astream(
                input_state,
                cfg,
                stream_mode=["messages", "values"],
            ):
                if mode == "values" and isinstance(chunk, dict) and out_messages is not None:
                    msgs = chunk.get("messages")
                    if isinstance(msgs, list):
                        out_messages[:] = list(msgs)
                await q.put(("stream", (mode, chunk)))
        except Exception as exc:
            logger.exception("Agent graph stream failed")
            await q.put(("sse", {"type": "error", "error": str(exc)}))
        finally:
            await q.put(None)

    task = asyncio.create_task(producer())

    start_payload: dict[str, Any] = {
        "type": "message_start",
        "conversation_id": conversation_id,
        "model": model,
    }
    if chat_mode is not None:
        start_payload["chat_mode"] = chat_mode
    yield sse_event(start_payload)

    try:
        while True:
            item = await q.get()
            if item is None:
                break
            kind, data = item
            if kind == "sse":
                yield sse_event(data)
                continue
            mode, chunk = data
            if mode == "messages":
                if isinstance(chunk, tuple) and len(chunk) >= 1:
                    tok = chunk[0]
                    if isinstance(tok, AIMessageChunk):
                        text = _text_from_chunk(tok)
                        if text:
                            yield sse_event({
                                "type": "content_block_delta",
                                "delta": {"type": "text_delta", "text": text},
                            })
            elif mode == "values":
                if not isinstance(chunk, dict):
                    continue
                msgs = chunk.get("messages")
                if not isinstance(msgs, list) or not msgs:
                    continue
                last = msgs[-1]
                if isinstance(last, AIMessage) and last.tool_calls:
                    sig = "|".join(
                        f"{tc.get('id', '')}:{tc.get('name', '')}"
                        for tc in (last.tool_calls or [])
                        if isinstance(tc, dict)
                    )
                    if sig and sig not in seen_tool_sig:
                        seen_tool_sig.add(sig)
                        for payload in _emit_tool_calls_from_ai(last, auto_approve):
                            yield sse_event(payload)
    finally:
        await task


async def get_final_messages_from_stream(
    graph: CompiledStateGraph,
    input_state: dict[str, Any],
    config: dict[str, Any],
) -> list[BaseMessage]:
    """Non-streaming invoke; used for sub-agents and tests."""
    out = await graph.ainvoke(input_state, config)
    return list(out.get("messages", []))
