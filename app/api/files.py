from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.dependencies import verify_auth
from app.utils.paths import is_image, is_text_file

router = APIRouter()


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Absolute or relative file path"),
    _auth: str | None = Depends(verify_auth),
):
    p = Path(path).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not p.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    if is_image(p):
        data = base64.b64encode(p.read_bytes()).decode()
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }.get(p.suffix.lower(), "application/octet-stream")
        return {"type": "image", "media_type": media, "data": data, "path": str(p)}

    if not is_text_file(p):
        raise HTTPException(status_code=400, detail="Binary file; not readable as text")

    content = p.read_text(encoding="utf-8", errors="replace")
    return {"type": "text", "content": content, "path": str(p)}


class WriteFileRequest(BaseModel):
    path: str
    content: str


@router.post("/write")
async def write_file(
    body: WriteFileRequest,
    _auth: str | None = Depends(verify_auth),
):
    p = Path(body.path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.content, encoding="utf-8")
    return {"written": True, "path": str(p), "size": len(body.content)}
