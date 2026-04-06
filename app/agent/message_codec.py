from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.models.messages import Message

logger = logging.getLogger(__name__)


def _tool_result_content_to_str(content: str | list[dict[str, Any]] | Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return json.dumps(content)
    return str(content)


def messages_to_langchain(messages: list[Message]) -> list[BaseMessage]:
    """Convert persisted Fast Code messages to LangChain messages."""
    out: list[BaseMessage] = []
    for m in messages:
        if m.role == "user":
            if isinstance(m.content, str):
                out.append(HumanMessage(content=m.content))
            elif isinstance(m.content, list):
                for block in m.content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        out.append(HumanMessage(content=str(block.get("text", ""))))
                    elif btype == "tool_result":
                        out.append(
                            ToolMessage(
                                content=_tool_result_content_to_str(block.get("content", "")),
                                tool_call_id=str(block.get("tool_use_id", "")),
                            )
                        )
            else:
                out.append(HumanMessage(content=str(m.content)))
        elif m.role == "assistant":
            if isinstance(m.content, str):
                out.append(AIMessage(content=m.content))
            elif isinstance(m.content, list):
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for block in m.content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(str(block.get("text", "")))
                    elif btype == "tool_use":
                        inp = block.get("input") or {}
                        tid = str(block.get("id", ""))
                        name = str(block.get("name", ""))
                        tool_calls.append({"name": name, "args": inp, "id": tid})
                text = "\n".join(text_parts).strip()
                if tool_calls:
                    out.append(AIMessage(content=text or "", tool_calls=tool_calls))
                else:
                    out.append(AIMessage(content=text))
            else:
                out.append(AIMessage(content=str(m.content)))
    return out


def langchain_to_messages(lc: list[BaseMessage]) -> list[Message]:
    """Convert LangChain messages back to Fast Code Message models (no system messages)."""
    out: list[Message] = []
    i = 0
    while i < len(lc):
        m = lc[i]
        if isinstance(m, HumanMessage):
            out.append(Message(role="user", content=m.content if isinstance(m.content, str) else str(m.content)))
            i += 1
        elif isinstance(m, AIMessage):
            blocks: list[dict[str, Any]] = []
            content = m.content
            if isinstance(content, str) and content.strip():
                blocks.append({"type": "text", "text": content})
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        blocks.append({"type": "text", "text": str(part.get("text", ""))})
                    elif isinstance(part, str):
                        blocks.append({"type": "text", "text": part})
            for tc in m.tool_calls or []:
                if isinstance(tc, dict):
                    tid = str(tc.get("id", ""))
                    name = str(tc.get("name", ""))
                    args = tc.get("args")
                    if args is None and "arguments" in tc:
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
                    blocks.append({"type": "tool_use", "id": tid, "name": name, "input": args})
            if blocks:
                out.append(Message(role="assistant", content=blocks))
            elif not m.tool_calls:
                out.append(Message(role="assistant", content=str(content or "")))
            i += 1
            tr_blocks: list[dict[str, Any]] = []
            while i < len(lc) and isinstance(lc[i], ToolMessage):
                tm = lc[i]
                tr_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tm.tool_call_id,
                        "content": tm.content
                        if isinstance(tm.content, str)
                        else json.dumps(tm.content),
                        "is_error": getattr(tm, "status", None) == "error",
                    }
                )
                i += 1
            if tr_blocks:
                out.append(Message(role="user", content=tr_blocks))
        elif isinstance(m, ToolMessage):
            out.append(
                Message(
                    role="user",
                    content=[
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id,
                            "content": m.content
                            if isinstance(m.content, str)
                            else json.dumps(m.content),
                        }
                    ],
                )
            )
            i += 1
        else:
            logger.debug("Skipping unknown message type in codec: %s", type(m).__name__)
            i += 1
    return out
