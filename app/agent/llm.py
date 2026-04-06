from __future__ import annotations

from typing import Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings
from app.llm.router import provider_kind_for_model


def uses_max_completion_tokens(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")


def get_chat_model(
    model: str,
    *,
    provider: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = 0.2,
) -> BaseChatModel:
    """Return a LangChain chat model for Anthropic or OpenAI."""
    kind: Literal["anthropic", "openai"] = provider_kind_for_model(model, provider)
    mt = max_tokens if max_tokens else (
        settings.anthropic_max_tokens if kind == "anthropic" else settings.openai_max_tokens
    )

    if kind == "anthropic":
        return ChatAnthropic(
            model=model or settings.anthropic_model,
            api_key=settings.anthropic_api_key or None,
            max_tokens=mt,
            temperature=temperature,
        )

    kwargs: dict[str, Any] = {
        "model": model or settings.openai_model,
        "api_key": settings.openai_api_key or None,
        "temperature": temperature,
    }
    if uses_max_completion_tokens(model or settings.openai_model):
        kwargs["max_completion_tokens"] = mt
    else:
        kwargs["max_tokens"] = mt
    return ChatOpenAI(**kwargs)
