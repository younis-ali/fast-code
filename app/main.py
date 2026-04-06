from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings

logger = logging.getLogger("fast_code")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Fast Code starting – anthropic_model=%s openai_model=%s",
        settings.anthropic_model,
        settings.openai_model,
    )

    from app.services.store import init_db
    await init_db()

    from app.agent.graph import compile_agent_graph
    from app.agent.runtime import set_compiled_graph
    from app.core.tool_registry import registry
    registry.discover()
    logger.info("Registered %d tools", len(registry))

    set_compiled_graph(compile_agent_graph(registry))
    logger.info("LangGraph agent compiled")

    yield

    logger.info("Shutting down")
    from app.services.store import close_db
    await close_db()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    app = FastAPI(
        title="Fast Code",
        description="AI coding assistant with tool execution, streaming chat, and MCP server.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"error": str(exc)}, status_code=500)

    from app.api.health import router as health_router
    from app.api.chat import router as chat_router
    from app.api.sessions import router as sessions_router
    from app.api.files import router as files_router
    from app.api.tools import router as tools_router
    from app.api.mcp import router as mcp_router
    from app.api.ws import router as ws_router
    from app.api.workspace_meta import router as workspace_meta_router

    app.include_router(health_router, tags=["Health"])
    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(sessions_router, prefix="/api", tags=["Sessions"])
    app.include_router(files_router, prefix="/api/files", tags=["Files"])
    app.include_router(tools_router, prefix="/api", tags=["Tools"])
    app.include_router(mcp_router, tags=["MCP"])
    app.include_router(ws_router, tags=["WebSocket"])
    app.include_router(workspace_meta_router, prefix="/api", tags=["Workspace"])

    web_dir = Path(__file__).resolve().parent.parent / "web"
    if (web_dir / "static").is_dir():
        app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")

    templates = Jinja2Templates(directory=str(web_dir / "templates"))

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse(request, "index.html")

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
