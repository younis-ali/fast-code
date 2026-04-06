from __future__ import annotations

import pytest

from app.models.sessions import Session, SessionConfig


def test_session_creation():
    session = Session()
    assert session.id.startswith("sess_")
    assert session.conversation_id == ""
    assert session.config.max_turns == 100


def test_session_config():
    config = SessionConfig(model="claude-opus-4-20250514", max_turns=50)
    session = Session(config=config)
    assert session.config.model == "claude-opus-4-20250514"
    assert session.config.max_turns == 50
