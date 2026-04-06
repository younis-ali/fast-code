from __future__ import annotations

from typing import Literal

from app.config import settings


def is_openai_model(model: str) -> bool:
    m = (model or "").strip().lower()
    return m.startswith("gpt-")


def provider_kind_for_model(model: str, explicit: str | None) -> Literal["anthropic", "openai"]:
    e = (explicit or "").strip().lower()
    if e == "openai":
        return "openai"
    if e == "anthropic":
        return "anthropic"
    return "openai" if is_openai_model(model) else "anthropic"


def validate_provider_credentials(kind: Literal["anthropic", "openai"]) -> str | None:
    if kind == "anthropic" and not settings.anthropic_api_key:
        return "ANTHROPIC_API_KEY is not configured"
    if kind == "openai" and not settings.openai_api_key:
        return "OPENAI_API_KEY is not configured"
    return None
