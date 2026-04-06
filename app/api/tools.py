from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import verify_auth
from app.core.tool_registry import registry

router = APIRouter()


@router.get("/tools")
async def list_tools(_auth: str | None = Depends(verify_auth)):
    return {"tools": [d.model_dump() for d in registry.list_definitions()]}
