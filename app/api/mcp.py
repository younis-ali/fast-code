from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/mcp/health")
async def mcp_health():
    return {"status": "ok", "server": "fast-code-explorer", "version": "1.1.0"}


@router.get("/mcp/tools")
async def mcp_tools():
    try:
        from mcp_explorer.server import mcp
        tools = await mcp.list_tools()
        return {"tools": [{"name": t.name, "description": t.description} for t in tools]}
    except ImportError:
        from app.core.tool_registry import registry
        defs = registry.list_definitions()
        return {
            "tools": [{"name": d.name, "description": d.description} for d in defs],
        }
    except Exception as exc:
        logger.exception("Failed to list MCP tools")
        return {"tools": [], "error": str(exc)}
