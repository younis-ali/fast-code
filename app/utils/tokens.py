from __future__ import annotations


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


CONTEXT_WINDOWS: dict[str, int] = {
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-haiku-3-20250307": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "gpt-4o-mini": 128_000,
    "gpt-5-mini": 128_000,
}

DEFAULT_CONTEXT_WINDOW = 200_000


def get_context_window(model: str) -> int:
    return CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW)
