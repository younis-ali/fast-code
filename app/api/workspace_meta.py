from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.responses import PlainTextResponse

from app.core.tool_registry import registry
from app.dependencies import verify_auth
from app.workspace.audit import run_structure_audit
from app.workspace.query_summary import WorkspaceQuerySummary

router = APIRouter()


@router.get("/workspace/summary", response_class=PlainTextResponse)
async def workspace_summary(_auth: str | None = Depends(verify_auth)):
    if not registry._tools:
        registry.discover()
    text = WorkspaceQuerySummary.from_app(registry).render_summary()
    return PlainTextResponse(text, media_type="text/markdown; charset=utf-8")


@router.get("/workspace/audit")
async def workspace_audit(_auth: str | None = Depends(verify_auth)):
    return run_structure_audit().to_dict()
