from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import aiosqlite

from app.config import settings
from app.models.conversations import Conversation, ConversationSummary
from app.models.messages import Message
from app.models.sessions import Session

logger = logging.getLogger(__name__)

_DB_PATH: Path = settings.data_dir / "fast_code.db"
_db: aiosqlite.Connection | None = None
_db_path_override: str | None = None


def set_db_path(path: str) -> None:
    global _db_path_override, _db
    _db_path_override = path
    _db = None


async def _get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = _db_path_override or str(_DB_PATH)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        try:
            await _db.close()
        except Exception:
            pass
        _db = None


async def init_db() -> None:
    db = await _get_db()
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New Conversation',
            model TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT '',
            messages TEXT NOT NULL DEFAULT '[]',
            total_input_tokens INTEGER NOT NULL DEFAULT 0,
            total_output_tokens INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL DEFAULT '',
            config TEXT NOT NULL DEFAULT '{}',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        """
    )
    await db.commit()
    logger.info("Database initialized at %s", _DB_PATH)


async def save_conversation(conv: Conversation) -> None:
    db = await _get_db()
    await db.execute(
        """
        INSERT OR REPLACE INTO conversations
            (id, title, model, system_prompt, messages,
             total_input_tokens, total_output_tokens, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conv.id,
            conv.title,
            conv.model,
            conv.system_prompt,
            json.dumps([m.model_dump() for m in conv.messages]),
            conv.total_input_tokens,
            conv.total_output_tokens,
            conv.created_at,
            conv.updated_at,
        ),
    )
    await db.commit()


async def load_conversation(conversation_id: str) -> Conversation | None:
    db = await _get_db()
    cursor = await db.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    raw_msgs: list[dict] = json.loads(row["messages"])
    messages = [Message.model_validate(m) for m in raw_msgs]
    return Conversation(
        id=row["id"],
        title=row["title"],
        model=row["model"],
        system_prompt=row["system_prompt"],
        messages=messages,
        total_input_tokens=row["total_input_tokens"],
        total_output_tokens=row["total_output_tokens"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_conversations(limit: int = 50, offset: int = 0) -> list[ConversationSummary]:
    db = await _get_db()
    cursor = await db.execute(
        """
        SELECT id, title, model, messages,
               total_input_tokens, total_output_tokens, created_at, updated_at
        FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = await cursor.fetchall()
    results: list[ConversationSummary] = []
    for row in rows:
        msgs = json.loads(row["messages"])
        results.append(
            ConversationSummary(
                id=row["id"],
                title=row["title"],
                message_count=len(msgs),
                model=row["model"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                total_input_tokens=row["total_input_tokens"],
                total_output_tokens=row["total_output_tokens"],
            )
        )
    return results


async def delete_conversation(conversation_id: str) -> bool:
    db = await _get_db()
    cursor = await db.execute(
        "DELETE FROM conversations WHERE id = ?", (conversation_id,)
    )
    await db.commit()
    return cursor.rowcount > 0


async def save_session(session: Session) -> None:
    db = await _get_db()
    await db.execute(
        """
        INSERT OR REPLACE INTO sessions
            (id, conversation_id, config, metadata, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session.id,
            session.conversation_id,
            session.config.model_dump_json(),
            json.dumps(session.metadata),
            session.created_at,
            session.updated_at,
        ),
    )
    await db.commit()


async def load_session(session_id: str) -> Session | None:
    db = await _get_db()
    cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return Session(
        id=row["id"],
        conversation_id=row["conversation_id"],
        config=json.loads(row["config"]),
        metadata=json.loads(row["metadata"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_sessions(limit: int = 50) -> list[Session]:
    db = await _get_db()
    cursor = await db.execute(
        "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [
        Session(
            id=row["id"],
            conversation_id=row["conversation_id"],
            config=json.loads(row["config"]),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def delete_session(session_id: str) -> bool:
    db = await _get_db()
    cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()
    return cursor.rowcount > 0
