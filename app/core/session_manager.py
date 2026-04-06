from __future__ import annotations

import logging

from app.models.conversations import Conversation
from app.models.sessions import Session, SessionConfig
from app.services import store

logger = logging.getLogger(__name__)


async def create_session(config: SessionConfig | None = None) -> Session:
    """Create a new session with an associated conversation."""
    conv = Conversation(model=config.model if config else "")
    await store.save_conversation(conv)

    session = Session(
        conversation_id=conv.id,
        config=config or SessionConfig(),
    )
    await store.save_session(session)
    logger.info("Created session %s with conversation %s", session.id, conv.id)
    return session


async def resume_session(session_id: str) -> tuple[Session, Conversation] | None:
    """Resume an existing session and its conversation."""
    session = await store.load_session(session_id)
    if session is None:
        return None

    conv = await store.load_conversation(session.conversation_id)
    if conv is None:
        return None

    return session, conv
