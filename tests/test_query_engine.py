from __future__ import annotations

import pytest

from app.models.conversations import Conversation
from app.models.messages import Message
from app.utils.tokens import estimate_tokens, get_context_window


def test_estimate_tokens():
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("a" * 400) == 100


def test_context_window():
    assert get_context_window("claude-sonnet-4-20250514") == 200_000
    assert get_context_window("unknown-model") == 200_000


def test_conversation_add_message():
    conv = Conversation()
    assert len(conv.messages) == 0

    conv.add_message(Message(role="user", content="hello"))
    assert len(conv.messages) == 1
    assert conv.messages[0].content == "hello"


def test_conversation_to_api_messages():
    conv = Conversation()
    conv.add_message(Message(role="user", content="hi"))
    conv.add_message(Message(role="assistant", content="hello"))

    api_msgs = conv.to_api_messages()
    assert len(api_msgs) == 2
    assert api_msgs[0]["role"] == "user"
    assert api_msgs[1]["role"] == "assistant"


def test_message_to_api_param():
    msg = Message(role="user", content="test")
    param = msg.to_api_param()
    assert param == {"role": "user", "content": "test"}
