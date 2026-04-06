from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from app.agent.llm import get_chat_model
from app.agent.message_codec import langchain_to_messages, messages_to_langchain
from app.agent.runtime import get_compiled_graph
from app.agent.streaming import stream_compiled_graph
from app.agent.tools import registry_tools_to_langchain
from app.config import settings
from app.core.chat_context import reset_chat_mode, set_chat_mode
from app.core.chat_modes import allowed_tool_names_for_mode, normalize_chat_mode
from app.core.prompt_builder import build_system_prompt
from app.core.tool_registry import registry
from app.llm.router import provider_kind_for_model, validate_provider_credentials
from app.models.conversations import Conversation
from app.models.messages import Message
from app.services import store
from app.utils.streaming import sse_done, sse_event

logger = logging.getLogger(__name__)


async def query_stream(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    system: str | None = None,
    conversation_id: str | None = None,
    max_tokens: int | None = None,
    provider: str | None = None,
    auto_approve: bool = False,
    mode: str | None = None,
) -> AsyncIterator[str]:
    """Run the LangGraph agent, yielding SSE frames for the client."""
    chat_mode = normalize_chat_mode(mode)
    mode_token = set_chat_mode(chat_mode)
    conv: Conversation | None = None
    cid = (conversation_id or "").strip()
    try:
        if cid:
            conv = await store.load_conversation(cid)
            if conv is None:
                yield sse_event({
                    "type": "error",
                    "error": (
                        f"Conversation not found: {cid}. "
                        "Start a new chat or omit conversation_id for a new thread."
                    ),
                })
                yield sse_done()
                return

        eff_for_kind = (model or (conv.model if conv else "") or "").strip()
        kind = provider_kind_for_model(eff_for_kind, provider)
        if not eff_for_kind and not (provider or "").strip():
            if settings.openai_api_key and not settings.anthropic_api_key:
                kind = "openai"

        err = validate_provider_credentials(kind)
        if err:
            yield sse_event({"type": "error", "error": err})
            yield sse_done()
            return

        if conv is None:
            default_m = settings.openai_model if kind == "openai" else settings.anthropic_model
            conv = Conversation(model=model or default_m)

        for msg in messages:
            conv.add_message(Message(role=msg["role"], content=msg["content"]))

        system_prompt = build_system_prompt(system, mode=chat_mode)
        effective_model = model or conv.model or (
            settings.openai_model if kind == "openai" else settings.anthropic_model
        )
        conv.model = effective_model

        allowed = allowed_tool_names_for_mode(chat_mode)
        lc_tools = registry_tools_to_langchain(registry, allowed_names=allowed)
        llm = get_chat_model(effective_model, provider=provider, max_tokens=max_tokens)
        llm = llm.bind_tools(lc_tools)

        lc_messages = messages_to_langchain(conv.messages)
        if not lc_messages:
            yield sse_event({"type": "error", "error": "No messages to send."})
            yield sse_done()
            return

        graph = get_compiled_graph()
        config: dict[str, Any] = {
            "configurable": {
                "llm": llm,
                "system_prompt": system_prompt,
                "auto_approve": auto_approve,
            },
            "recursion_limit": 100,
        }

        final_lc: list[Any] = []

        logger.info(
            "LangGraph agent run: conv=%s model=%s provider=%s mode=%s msgs=%d auto_approve=%s",
            conv.id, effective_model, kind, chat_mode, len(lc_messages), auto_approve,
        )

        async for frame in stream_compiled_graph(
            graph,
            {"messages": lc_messages},
            config,
            conversation_id=conv.id,
            model=effective_model,
            auto_approve=auto_approve,
            out_messages=final_lc,
            chat_mode=chat_mode,
        ):
            yield frame

        if final_lc:
            conv.messages = langchain_to_messages(list(final_lc))

        if conv.title == "New Conversation" and conv.messages:
            for m in conv.messages:
                if m.role == "user":
                    text = m.content if isinstance(m.content, str) else ""
                    if text:
                        conv.title = text[:80].strip()
                    break

        await store.save_conversation(conv)

        yield sse_event({
            "type": "message_stop",
            "conversation_id": conv.id,
            "usage": {
                "input_tokens": conv.total_input_tokens,
                "output_tokens": conv.total_output_tokens,
            },
        })
        yield sse_done()
    finally:
        reset_chat_mode(mode_token)
