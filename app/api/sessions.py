from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import verify_auth
from app.models.conversations import Conversation, ConversationSummary
from app.models.sessions import Session, SessionConfig
from app.services import store

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    _auth: str | None = Depends(verify_auth),
):
    return await store.list_conversations(limit=limit, offset=offset)


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    title: str = "New Conversation",
    model: str = "",
    _auth: str | None = Depends(verify_auth),
):
    conv = Conversation(title=title, model=model)
    await store.save_conversation(conv)
    return conv


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    _auth: str | None = Depends(verify_auth),
):
    conv = await store.load_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    _auth: str | None = Depends(verify_auth),
):
    deleted = await store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


class CreateSessionRequest(BaseModel):
    conversation_id: str = ""
    config: SessionConfig = SessionConfig()


@router.get("/sessions", response_model=list[Session])
async def list_sessions(
    limit: int = 50,
    _auth: str | None = Depends(verify_auth),
):
    return await store.list_sessions(limit=limit)


@router.post("/sessions", response_model=Session)
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    _auth: str | None = Depends(verify_auth),
):
    session = Session(conversation_id=body.conversation_id, config=body.config)
    await store.save_session(session)
    return session


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    _auth: str | None = Depends(verify_auth),
):
    session = await store.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    _auth: str | None = Depends(verify_auth),
):
    deleted = await store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}
