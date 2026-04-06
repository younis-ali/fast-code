from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.dependencies import verify_auth

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: str = ""
    system: str = ""
    conversation_id: str = ""
    stream: bool = True
    max_tokens: int = 0
    provider: str = ""
    work_dir: str = ""
    auto_approve: bool = False
    mode: str = "agent"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    _auth: str | None = Depends(verify_auth),
):
    from app.core.query_engine import query_stream

    return StreamingResponse(
        query_stream(
            messages=body.messages,
            model=body.model or None,
            system=body.system or None,
            conversation_id=body.conversation_id or None,
            max_tokens=body.max_tokens or None,
            provider=body.provider or None,
            auto_approve=body.auto_approve,
            mode=body.mode or None,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class ToolApproveRequest(BaseModel):
    request_id: str
    approve_all: bool = False
    approved_ids: list[str] = []
    denied_ids: list[str] = []


@router.post("/tool-approve")
async def tool_approve(
    body: ToolApproveRequest,
    _auth: str | None = Depends(verify_auth),
):
    from app.core.approval import resolve_approval

    ok = resolve_approval(
        body.request_id,
        approve_all=body.approve_all,
        approved_ids=body.approved_ids,
        denied_ids=body.denied_ids,
    )
    if not ok:
        return {"resolved": False, "error": "Approval request not found or already resolved."}
    return {"resolved": True}


@router.get("/files/list")
async def list_files(
    path: str = Query("", description="Directory or partial path"),
    _auth: str | None = Depends(verify_auth),
):
    base = settings.work_dir or os.getcwd()

    if not path or path == "/":
        target = Path(base)
    elif path.startswith("/"):
        target = Path(path)
    else:
        target = Path(base) / path

    target = target.resolve()

    if target.is_file():
        target = target.parent

    if not target.is_dir():
        parent = target.parent
        prefix = target.name.lower()
        if parent.is_dir():
            entries = _list_dir(parent, prefix_filter=prefix, limit=30)
            return {"base": str(parent), "entries": entries}
        return {"base": str(target), "entries": []}

    entries = _list_dir(target, limit=50)
    return {"base": str(target), "entries": entries}


def _list_dir(
    directory: Path,
    *,
    prefix_filter: str = "",
    limit: int = 50,
) -> list[dict[str, str]]:
    try:
        items = list(directory.iterdir())
    except PermissionError:
        return []

    dirs = []
    files = []
    for item in items:
        name = item.name
        if name.startswith("."):
            continue
        if prefix_filter and not name.lower().startswith(prefix_filter):
            continue
        entry = {
            "name": name,
            "path": str(item),
            "type": "directory" if item.is_dir() else "file",
        }
        if item.is_dir():
            dirs.append(entry)
        else:
            files.append(entry)

    dirs.sort(key=lambda e: e["name"].lower())
    files.sort(key=lambda e: e["name"].lower())
    return (dirs + files)[:limit]
