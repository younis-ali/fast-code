from __future__ import annotations

import pytest

from app.agent.llm import uses_max_completion_tokens
from app.llm.router import is_openai_model, provider_kind_for_model


def test_uses_max_completion_tokens() -> None:
    assert uses_max_completion_tokens("gpt-5-mini") is True
    assert uses_max_completion_tokens("gpt-4o-mini") is False


def test_is_openai_model() -> None:
    assert is_openai_model("gpt-4o-mini") is True
    assert is_openai_model("GPT-5-mini") is True
    assert is_openai_model("claude-sonnet-4-20250514") is False


@pytest.mark.parametrize(
    ("model", "explicit", "expected"),
    [
        ("gpt-4o-mini", None, "openai"),
        ("claude-sonnet-4-20250514", None, "anthropic"),
        ("", "openai", "openai"),
        ("", "anthropic", "anthropic"),
    ],
)
def test_provider_kind_for_model(model: str, explicit: str | None, expected: str) -> None:
    assert provider_kind_for_model(model, explicit) == expected
