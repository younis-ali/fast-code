from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from app.agent.llm import get_chat_model
from app.models.conversations import Conversation
from app.utils.tokens import estimate_tokens, get_context_window

logger = logging.getLogger(__name__)


def conversation_token_estimate(conv: Conversation) -> int:
    """Rough estimate of the total tokens in the conversation."""
    total = 0
    for msg in conv.messages:
        if isinstance(msg.content, str):
            total += estimate_tokens(msg.content)
        elif isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    content = block.get("content", "")
                    total += estimate_tokens(str(text or content))
    return total


async def compact_conversation(conv: Conversation) -> Conversation:
    """Summarize older messages to reduce context size while preserving meaning."""
    if len(conv.messages) <= 4:
        return conv

    context_window = get_context_window(conv.model)
    current_tokens = conversation_token_estimate(conv)

    if current_tokens < context_window * 0.75:
        return conv

    to_summarize = conv.messages[:-4]
    keep = conv.messages[-4:]

    summary_text_parts: list[str] = []
    for msg in to_summarize:
        if isinstance(msg.content, str):
            summary_text_parts.append(f"{msg.role}: {msg.content[:500]}")
        elif isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    summary_text_parts.append(f"{msg.role}: {block['text'][:500]}")

    summary_input = "\n".join(summary_text_parts)

    try:
        llm = get_chat_model(conv.model, max_tokens=2048)
        resp = await llm.ainvoke(
            [HumanMessage(content=f"Summarize this conversation concisely:\n\n{summary_input}")]
        )
        summary = "Conversation summary unavailable."
        content: Any = getattr(resp, "content", None)
        if content:
            summary = str(content)
    except Exception:
        logger.exception("Failed to create conversation summary")
        summary = f"[Previous {len(to_summarize)} messages summarized]"

    from app.models.messages import Message

    conv.messages = [
        Message(role="user", content=f"[Conversation summary]\n{summary}"),
        Message(role="assistant", content="Understood. I have the context from the summary. Let's continue."),
        *keep,
    ]

    logger.info(
        "Compacted conversation %s from %d to %d messages",
        conv.id,
        len(to_summarize) + len(keep),
        len(conv.messages),
    )
    return conv
