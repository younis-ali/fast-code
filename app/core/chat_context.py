from __future__ import annotations

from contextvars import ContextVar, Token

from app.core.chat_modes import ChatMode, normalize_chat_mode

_current_chat_mode: ContextVar[ChatMode] = ContextVar("current_chat_mode", default="agent")


def get_chat_mode() -> ChatMode:
    return _current_chat_mode.get()


def set_chat_mode(mode: str | ChatMode | None) -> Token:
    """Return a token for reset_chat_mode()."""
    return _current_chat_mode.set(normalize_chat_mode(mode))


def reset_chat_mode(token: Token) -> None:
    _current_chat_mode.reset(token)
